"""The render sync loop between the engine and a browser.

A render is pushed down the WebSocket with its world state, the browser
acknowledges renders over the same socket, and the engine only waits when the
browser has fallen a window of renders behind.
"""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from engine.device.manager.web import manager as manager_module
from engine.device.manager.web.client import ClientManager
from engine.device.manager.web.manager import WebDeviceManager
from engine.device.web.server.server_socket import GameServerSocket


def _manager(synced: int) -> WebDeviceManager:
    manager = object.__new__(WebDeviceManager)
    manager.client_manager = ClientManager()
    manager.client_manager.client_synced[0] = synced
    manager.headless_players = set()
    return manager


def _device(last_render_id: int):
    world = SimpleNamespace(render=SimpleNamespace(last_render_id=last_render_id))
    controller = SimpleNamespace(world=world, game=SimpleNamespace(state=SimpleNamespace(is_running=True)))
    return SimpleNamespace(player_id=0, is_connected=True, controller=controller)


class TheEngineWaitsOnlyWhenTheBrowserIsFarBehind(unittest.TestCase):

    def test_a_browser_inside_the_window_does_not_hold_the_engine(self):
        with patch.object(manager_module.RENDER_AHEAD_WINDOW, 'value', 24):
            self.assertTrue(_manager(synced=10).CheckSync(_device(last_render_id=30)))

    def test_a_browser_past_the_window_holds_the_engine(self):
        with patch.object(manager_module.RENDER_AHEAD_WINDOW, 'value', 24):
            self.assertFalse(_manager(synced=5).CheckSync(_device(last_render_id=30)))

    def test_a_zero_window_is_the_old_lock_step(self):
        with patch.object(manager_module.RENDER_AHEAD_WINDOW, 'value', 0):
            self.assertFalse(_manager(synced=29).CheckSync(_device(last_render_id=30)))
            self.assertTrue(_manager(synced=30).CheckSync(_device(last_render_id=30)))


class AcknowledgementsArriveOverTheSocket(unittest.TestCase):

    def _server(self):
        calls = []
        server = object.__new__(GameServerSocket)
        server.device_manager = SimpleNamespace(
            ClientUpdateRenderId=lambda player_id, render_id, game_id: calls.append((player_id, render_id, game_id)))
        return server, calls

    def test_one_message_updates_every_seat_the_socket_plays(self):
        server, calls = self._server()
        server.OnClientUpdated("client_updated 12 3", [0, 1])
        self.assertEqual(calls, [(0, 12, 3), (1, 12, 3)])

    def test_a_malformed_message_is_ignored(self):
        server, calls = self._server()
        server.OnClientUpdated("client_updated twelve", [0])
        server.OnClientUpdated("client_updated", [0])
        self.assertEqual(calls, [])


class TheWorldIsSentOncePerRender(unittest.TestCase):

    def test_a_second_seat_on_the_same_socket_does_not_get_it_again(self):
        client = ClientManager.ClientInfo([0, 1], "", None, 0)
        self.assertTrue(client.NeedsWorld(game_id=1, render_id=7))
        self.assertFalse(client.NeedsWorld(game_id=1, render_id=7))

    def test_a_new_render_or_a_new_game_is_sent(self):
        client = ClientManager.ClientInfo([0], "", None, 0)
        self.assertTrue(client.NeedsWorld(game_id=1, render_id=7))
        self.assertTrue(client.NeedsWorld(game_id=1, render_id=8))
        self.assertTrue(client.NeedsWorld(game_id=2, render_id=8))


if __name__ == '__main__':
    unittest.main()
