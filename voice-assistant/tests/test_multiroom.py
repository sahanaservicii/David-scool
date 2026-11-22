import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from assistant.core.rooms import normalize_rooms, resolve_room, room_summary
from assistant.nlu.router import IntentRouter
from assistant.core.engine import AssistantEngine


class TestRooms(unittest.TestCase):
    def setUp(self):
        self.rooms = normalize_rooms([
            {"id": "kitchen", "name": "Кухня", "aliases": ["на кухне", "кухне"], "satellite_id": "sat_k", "media_player": "media_player.kitchen", "tts_player": "media_player.kitchen"},
            {"id": "living_room", "name": "Гостиная", "aliases": ["зал", "в зале"], "satellite_id": "sat_l", "media_player": "media_player.living"},
            {"id": "bedroom", "name": "Спальня", "aliases": ["в спальне"], "satellite_id": "sat_b", "media_player": "media_player.bed"},
        ])

    def test_resolve_by_id_name_alias(self):
        self.assertEqual(resolve_room(self.rooms, hint="kitchen").get("id"), "kitchen")
        self.assertEqual(resolve_room(self.rooms, hint="Гостиная").get("id"), "living_room")
        self.assertEqual(resolve_room(self.rooms, hint="в спальне").get("id"), "bedroom")

    def test_resolve_by_text(self):
        self.assertEqual(resolve_room(self.rooms, text="включи музыку в гостиной").get("id"), "living_room")
        self.assertEqual(resolve_room(self.rooms, text="поставь джаз на кухне").get("id"), "kitchen")

    def test_resolve_by_satellite(self):
        self.assertEqual(resolve_room(self.rooms, satellite_id="sat_b").get("id"), "bedroom")

    def test_generic_here_uses_context(self):
        self.assertEqual(resolve_room(self.rooms, text="включи музыку здесь", context_room_id="kitchen").get("id"), "kitchen")

    def test_room_summary(self):
        s = room_summary(self.rooms[0])
        self.assertEqual(s["id"], "kitchen")
        self.assertEqual(s["media_player"], "media_player.kitchen")
        self.assertEqual(s["satellite_id"], "sat_k")


class TestRouterMultiroomMusic(unittest.TestCase):
    def setUp(self):
        self.r = IntentRouter()

    def test_media_play_routes_to_ha(self):
        ir = self.r.route('включи музыку в гостиной')
        self.assertEqual(ir.intent, 'media_control')
        self.assertEqual(ir.skill, 'ha')

    def test_media_volume_routes_to_ha(self):
        ir = self.r.route('сделай громче')
        self.assertEqual(ir.intent, 'media_control')
        self.assertEqual(ir.skill, 'ha')

    def test_light_in_room_routes_to_ha(self):
        ir = self.r.route('включи свет в кухне')
        self.assertEqual(ir.intent, 'ha_control')
        self.assertEqual(ir.skill, 'ha')


class TestEngineRoomContext(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.engine = AssistantEngine()
        # isolate storage
        from assistant.core.storage import Storage
        self.engine.storage = Storage(Path(self.tmp.name) / 'test.db')
        # override rooms for deterministic tests
        self.engine.cfg['rooms'] = [
            {"id": "kitchen", "name": "Кухня", "aliases": ["на кухне"], "satellite_id": "sat_k", "media_player": "media_player.kitchen"},
            {"id": "living", "name": "Гостиная", "aliases": ["в гостиной", "зал"], "satellite_id": "sat_l", "media_player": "media_player.living"},
        ]

    def tearDown(self):
        self.tmp.cleanup()

    def test_process_with_room_meta(self):
        r = self.engine.process('привет', session_id='r1', meta={'room': 'kitchen'})
        self.assertEqual((r.get('room') or {}).get('id'), 'kitchen')
        self.assertEqual((r.get('room') or {}).get('media_player'), 'media_player.kitchen')

    def test_process_resolves_room_from_text(self):
        r = self.engine.process('включи свет в гостиной', session_id='r2')
        # even if HA not reachable, engine should resolve room context
        self.assertEqual((r.get('room') or {}).get('id'), 'living')

    def test_process_resolves_room_from_satellite(self):
        r = self.engine.process('привет', session_id='r3', meta={'satellite_id': 'sat_l'})
        self.assertEqual((r.get('room') or {}).get('id'), 'living')

    def test_status_includes_room_summaries(self):
        st = self.engine.status(quick=True)
        rooms = st.get('rooms') or []
        self.assertTrue(any(x.get('id') == 'kitchen' and x.get('media_player') == 'media_player.kitchen' for x in rooms))


if __name__ == '__main__':
    unittest.main()
