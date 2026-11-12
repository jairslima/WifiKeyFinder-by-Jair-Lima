"""Testes unitários e de integração de interface para o WiFi Key Finder by Jair Lima."""

from __future__ import annotations

import tkinter as tk
from typing import List, Tuple
import unittest

from app import MASKED_VALUE, WifiKeyFinderApp, build_demo_service
from wlan_service import (
    WlanService,
    WlanStatus,
    decode_console_bytes,
    resolve_netsh_path,
)


class TestWlanServiceParsing(unittest.TestCase):
    """Valida o parsing da saída do netsh em diferentes idiomas, encodings e cenários."""

    def test_parse_profiles_pt_br_and_special_chars(self) -> None:
        raw_pt = (
            "\nPerfis na interface Wi-Fi:\n\n"
            "Perfis de política de grupo (somente leitura)\n"
            "---------------------------------\n"
            "    <Nenhum>\n\n"
            "Perfis de usuários\n"
            "-------------\n"
            "    Todos os Perfis de Usuários : Casa_Fibra_5G\n"
            "    Todos os Perfis de Usuários : Café & Pão: Visitantes\n"
            "    Perfil de Usuário Atual     : Hotspot_Celular\n"
        )
        res = WlanService.parse_profiles_output(0, raw_pt)
        self.assertEqual(res.status, WlanStatus.SUCCESS)
        self.assertEqual(
            res.profiles,
            ["Casa_Fibra_5G", "Café & Pão: Visitantes", "Hotspot_Celular"],
        )

    def test_parse_profiles_en_us(self) -> None:
        raw_en = (
            "\nProfiles on interface Wi-Fi:\n\n"
            "Group policy profiles (read only)\n"
            "---------------------------------\n"
            "    <None>\n\n"
            "User profiles\n"
            "-------------\n"
            "    All User Profile     : Office_Network\n"
            "    All User Profile     : HomeWiFi_2.4G\n"
        )
        res = WlanService.parse_profiles_output(0, raw_en)
        self.assertEqual(res.status, WlanStatus.SUCCESS)
        self.assertEqual(res.profiles, ["Office_Network", "HomeWiFi_2.4G"])

    def test_parse_profiles_empty_saved_list(self) -> None:
        raw_empty = (
            "\nPerfis na interface Wi-Fi:\n\n"
            "Perfis de usuários\n"
            "-------------\n"
            "    <Nenhum>\n"
        )
        res = WlanService.parse_profiles_output(0, raw_empty)
        self.assertEqual(res.status, WlanStatus.NO_PROFILES)
        self.assertEqual(res.profiles, [])
        self.assertIn("Nenhuma rede Wi-Fi salva", res.message)

    def test_parse_profiles_no_wireless_interface(self) -> None:
        raw_no_iface = "Não há nenhuma interface sem fio no sistema."
        res = WlanService.parse_profiles_output(0, raw_no_iface)
        self.assertEqual(res.status, WlanStatus.NO_INTERFACE_OR_SERVICE)

    def test_parse_profiles_wlansvc_stopped(self) -> None:
        raw_stopped = (
            "O Serviço de Configuração Automática sem Fio (wlansvc) não está em execução."
        )
        res = WlanService.parse_profiles_output(1, raw_stopped)
        self.assertEqual(res.status, WlanStatus.NO_INTERFACE_OR_SERVICE)

    def test_parse_profile_detail_with_password_pt_br(self) -> None:
        raw_detail = (
            "\nPerfil Casa_5G na interface Wi-Fi:\n"
            "=======================================================================\n\n"
            "Configurações de conectividade\n"
            "    Número de SSIDs        : 1\n"
            '    Nome do SSID           : "Casa_5G"\n'
            "Configurações de segurança\n"
            "    Autenticação           : WPA2-Personal\n"
            "    Codificação            : CCMP\n"
            "    Chave de segurança     : Presente\n"
            "    Conteúdo da Chave      : Senha:Com:DoisPontos#2026\n"
        )
        det = WlanService.parse_profile_detail_output("Casa_5G", 0, raw_detail)
        self.assertEqual(det.status, WlanStatus.SUCCESS)
        self.assertEqual(det.ssid, "Casa_5G")
        self.assertEqual(det.auth_type, "WPA2-Personal")
        self.assertEqual(det.cipher_type, "CCMP")
        self.assertEqual(det.password, "Senha:Com:DoisPontos#2026")

    def test_parse_profile_detail_with_password_en_us(self) -> None:
        raw_detail_en = (
            "\nProfile Office_Network on interface Wi-Fi:\n"
            "Connectivity settings\n"
            '    SSID name              : "Office_Network"\n'
            "Security settings\n"
            "    Authentication         : WPA3-Personal\n"
            "    Cipher                 : GCMP\n"
            "    Security key           : Present\n"
            "    Key Content            : MySecretKey!99\n"
        )
        det = WlanService.parse_profile_detail_output(
            "Office_Network", 0, raw_detail_en
        )
        self.assertEqual(det.status, WlanStatus.SUCCESS)
        self.assertEqual(det.password, "MySecretKey!99")

    def test_parse_profile_detail_open_network_no_password(self) -> None:
        raw_open = (
            "\nPerfil Rede_Aberta na interface Wi-Fi:\n"
            "Configurações de conectividade\n"
            '    Nome do SSID           : "Rede_Aberta"\n'
            "Configurações de segurança\n"
            "    Autenticação           : Aberta\n"
            "    Codificação            : Nenhuma\n"
            "    Chave de segurança     : Ausente\n"
        )
        det = WlanService.parse_profile_detail_output("Rede_Aberta", 0, raw_open)
        self.assertEqual(det.status, WlanStatus.NO_PASSWORD)
        self.assertIsNone(det.password)
        self.assertIn("aberta", det.message.lower())

    def test_parse_profile_detail_permission_denied(self) -> None:
        raw_denied = "Acesso negado. Elevação necessária para executar esta operação."
        det = WlanService.parse_profile_detail_output("Corp_WiFi", 1, raw_denied)
        self.assertEqual(det.status, WlanStatus.PERMISSION_DENIED)
        self.assertIsNone(det.password)

    def test_decode_console_bytes_cp850_and_utf8(self) -> None:
        sample = "Configuração Automática: Café & Pão"
        encoded_cp850 = sample.encode("cp850")
        encoded_utf8 = sample.encode("utf-8")

        self.assertEqual(decode_console_bytes(encoded_cp850, "cp850"), sample)
        self.assertEqual(decode_console_bytes(encoded_utf8, "cp850"), sample)

    def test_resolve_netsh_path_points_to_system32(self) -> None:
        path = resolve_netsh_path()
        self.assertTrue(path.lower().endswith("netsh.exe"))

    def test_service_rejects_null_byte_in_profile_name(self) -> None:
        called = False

        def fake_runner(_args: List[str]) -> Tuple[int, bytes, bytes]:
            nonlocal called
            called = True
            return 0, b"", b""

        svc = WlanService(runner=fake_runner)
        res = svc.get_profile_details("Rede\x00Invalida")
        self.assertEqual(res.status, WlanStatus.ERROR)
        self.assertFalse(called)


class TestWifiKeyFinderGui(unittest.TestCase):
    """Testa o fluxo principal da interface gráfica com perfis com e sem senha."""

    def test_gui_default_masked_and_reveal_copy_flow(self) -> None:
        root = tk.Tk()
        root.withdraw()
        try:
            service = build_demo_service()
            app = WifiKeyFinderApp(root, service=service)
            app.refresh_profiles()

            # Confirma que carregou as 3 redes do serviço de demonstração
            self.assertEqual(len(app.all_profiles), 3)

            # 1) Primeira rede ("Casa_Fibra_5G") possui senha salva
            app.load_profile_details("Casa_Fibra_5G")
            self.assertEqual(app.ssid_var.get(), "Casa_Fibra_5G")
            # REGRA DE SEGURANÇA: Senha NUNCA aparece por padrão sem clique
            self.assertFalse(app.is_password_visible)
            self.assertEqual(app.password_display_var.get(), MASKED_VALUE)

            # Ao clicar em Mostrar senha, revela a senha real
            app.toggle_password_visibility()
            self.assertTrue(app.is_password_visible)
            self.assertEqual(app.password_display_var.get(), "Familia@2026#Segura!")

            # Ao clicar novamente, oculta a senha
            app.toggle_password_visibility()
            self.assertFalse(app.is_password_visible)
            self.assertEqual(app.password_display_var.get(), MASKED_VALUE)

            # 2) Segunda rede ("Café & Pão Visitantes") em CP850 com acentuação
            app.load_profile_details("Café & Pão Visitantes")
            self.assertFalse(app.is_password_visible)
            self.assertEqual(app.password_display_var.get(), MASKED_VALUE)
            app.toggle_password_visibility()
            self.assertEqual(app.password_display_var.get(), "PãoDeQueijoComCafé99")

            # 3) Terceira rede ("Aeroporto_WiFi_Aberto") sem senha salva localmente
            app.load_profile_details("Aeroporto_WiFi_Aberto")
            self.assertFalse(app.is_password_visible)
            self.assertEqual(
                app.password_display_var.get(), "(Sem senha salva neste perfil)"
            )
            self.assertEqual(str(app.toggle_pwd_btn["state"]), "disabled")
            self.assertEqual(str(app.copy_pwd_btn["state"]), "disabled")
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
