"Test undo, coverage 77%."
# Only test UndoDelegator so far.

from idlelib.undo import UndoDelegator
import unittest
from test.support import requires
requires('gui')

from unittest.mock import Mock, patch
from tkinter import Text, Tk
from idlelib.percolator import Percolator


class UndoDelegatorTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.root = Tk()
        cls.text = Text(cls.root)
        cls.percolator = Percolator(cls.text)

    @classmethod
    def tearDownClass(cls):
        cls.percolator.redir.close()
        del cls.percolator, cls.text
        cls.root.destroy()
        del cls.root

    def setUp(self):
        self.delegator = UndoDelegator()
        self.delegator.bell = Mock()
        self.percolator.insertfilter(self.delegator)

    def tearDown(self):
        self.percolator.removefilter(self.delegator)
        self.text.delete('1.0', 'end')
        self.delegator.resetcache()

    def test_undo_event(self):
        text = self.text

        text.insert('insert', 'foobar')
        text.insert('insert', 'h')
        text.event_generate('<<undo>>')
        self.assertEqual(text.get('1.0', 'end'), '\n')

        text.insert('insert', 'foo')
        text.insert('insert', 'bar')
        text.delete('1.2', '1.4')
        text.insert('insert', 'hello')
        text.event_generate('<<undo>>')
        self.assertEqual(text.get('1.0', '1.4'), 'foar')
        text.event_generate('<<undo>>')
        self.assertEqual(text.get('1.0', '1.6'), 'foobar')
        text.event_generate('<<undo>>')
        self.assertEqual(text.get('1.0', '1.3'), 'foo')
        text.event_generate('<<undo>>')
        self.delegator.undo_event('event')
        self.assertTrue(self.delegator.bell.called)

    def test_redo_event(self):
        text = self.text

        text.insert('insert', 'foo')
        text.insert('insert', 'bar')
        text.delete('1.0', '1.3')
        text.event_generate('<<undo>>')
        text.event_generate('<<redo>>')
        self.assertEqual(text.get('1.0', '1.3'), 'bar')
        text.event_generate('<<redo>>')
        self.assertTrue(self.delegator.bell.called)

    def test_dump_event(self):
        """
        Dump_event cannot be tested directly without changing
        environment variables. So, test statements in dump_event
        indirectly
        """
        text = self.text
        d = self.delegator

        text.insert('insert', 'foo')
        text.insert('insert', 'bar')
        text.delete('1.2', '1.4')
        self.assertTupleEqual((d.pointer, d.can_merge), (3, True))
        text.event_generate('<<undo>>')
        self.assertTupleEqual((d.pointer, d.can_merge), (2, False))

    def test_reset_undo(self):
        eq = self.assertEqual
        neq = self.assertNotEqual
        d = self.delegator
        orig_sch = d.saved_change_hook

        def set_text():
            self.text.insert('insert', 'spam')
            self.text.insert('insert', '\n')
            self.text.insert('insert', 'this is the second line')

        set_text()
        eq(d.pointer, len(d.undolist))
        neq(d.saved, d.pointer)

        # reset_undo should set saved to True and trigger the save change hook
        saved_change_hook = Mock()
        d.set_saved_change_hook(saved_change_hook)
        d.reset_undo()
        saved_change_hook.assert_called()
        eq(d.pointer, 0)
        eq(d.undolist, [])
        eq(d.undoblock, 0)
        eq(d.saved, d.pointer)

    def test_get_set_saved(self):
        # test the getter method get_saved
        # test the setter method set_saved
        # indirectly test check_saved
        d = self.delegator

        self.assertTrue(d.get_saved())
        self.text.insert('insert', 'a')
        self.assertFalse(d.get_saved())
        d.saved_change_hook = Mock()

        d.set_saved(True)
        self.assertEqual(d.pointer, d.saved)
        self.assertTrue(d.saved_change_hook.called)

        d.set_saved(False)
        self.assertEqual(d.saved, -1)
        self.assertTrue(d.saved_change_hook.called)

    def test_undo_start_stop(self):
        # test the undo_block_start and undo_block_stop methods
        text = self.text

        text.insert('insert', 'foo')
        self.delegator.undo_block_start()
        text.insert('insert', 'bar')
        text.insert('insert', 'bar')
        self.delegator.undo_block_stop()
        self.assertEqual(text.get('1.0', '1.3'), 'foo')

        # test another code path
        self.delegator.undo_block_start()
        text.insert('insert', 'bar')
        self.delegator.undo_block_stop()
        self.assertEqual(text.get('1.0', '1.3'), 'foo')

    def test_addcmd(self):
        text = self.text
        # when number of undo operations exceeds max_undo
        self.delegator.max_undo = max_undo = 10
        for i in range(max_undo + 10):
            text.insert('insert', 'foo')
            self.assertLessEqual(len(self.delegator.undolist), max_undo)


if __name__ == '__main__':
    unittest.main(verbosity=2, exit=False)
