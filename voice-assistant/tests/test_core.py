import os
import tempfile
import unittest
from pathlib import Path

# make package importable
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from assistant.core.engine import AssistantEngine
from assistant.nlu.router import IntentRouter


class TestRouter(unittest.TestCase):
    def setUp(self):
        self.r = IntentRouter()

    def test_time(self):
        ir = self.r.route('который час')
        self.assertEqual(ir.intent, 'time_now')

    def test_calc(self):
        ir = self.r.route('посчитай 2+2')
        self.assertEqual(ir.intent, 'calc')

    def test_note(self):
        ir = self.r.route('запиши купить хлеб')
        self.assertEqual(ir.intent, 'note_add')
        self.assertIn('хлеб', ir.entities.get('text',''))

    def test_timer(self):
        ir = self.r.route('таймер на 5 минут')
        self.assertEqual(ir.intent, 'timer_set')
        self.assertEqual(ir.entities.get('seconds'), 300)

    def test_search(self):
        ir = self.r.route('найди в интернете рецепт борща')
        self.assertEqual(ir.intent, 'search')
        self.assertTrue(ir.entities.get('query'))


class TestEngine(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        # use temp data dir via config override file? easier: construct engine and patch storage path
        self.engine = AssistantEngine()
        # redirect storage to temp by replacing
        from assistant.core.storage import Storage
        self.engine.storage = Storage(Path(self.tmp.name) / 'test.db')
        # re-register skills bound to storage? skills hold reference to storage passed in init
        # rebuild skills with new storage
        self.engine.registry = __import__('assistant.skills.base', fromlist=['SkillRegistry']).SkillRegistry()
        from assistant.skills.smalltalk import SmalltalkSkill
        from assistant.skills.time_skill import TimeSkill
        from assistant.skills.calc_skill import CalcSkill
        from assistant.skills.notes_skill import NotesSkill
        from assistant.skills.timer_skill import TimerSkill
        from assistant.skills.help_skill import HelpSkill
        from assistant.skills.system_skill import SystemSkill
        from assistant.skills.search_skill import SearchSkill
        from assistant.skills.fallback_skill import FallbackSkill
        cfg, st = self.engine.cfg, self.engine.storage
        for s in [SmalltalkSkill(cfg,st),TimeSkill(cfg,st),CalcSkill(cfg,st),NotesSkill(cfg,st),TimerSkill(cfg,st),HelpSkill(cfg,st),SystemSkill(cfg,st),SearchSkill(cfg,st),FallbackSkill(cfg,st)]:
            self.engine.registry.register(s)

    def tearDown(self):
        self.tmp.cleanup()

    def test_greeting(self):
        r = self.engine.process('привет', session_id='t1')
        self.assertTrue(r['text'])
        self.assertIn(r['intent'], ('greeting','how_are_you','who_are_you','thanks','goodbye','fallback'))

    def test_calc(self):
        r = self.engine.process('посчитай 2+2*2', session_id='t2')
        self.assertIn('6', r['text'])

    def test_notes(self):
        r = self.engine.process('запиши тестовая заметка', session_id='t3')
        self.assertIn('Записал', r['text'])
        r2 = self.engine.process('мои заметки', session_id='t3')
        self.assertIn('тестовая заметка', r2['text'])


if __name__ == '__main__':
    unittest.main()
