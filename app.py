"""WiFi Key Finder by Jair Lima (v1.0.0)

Utilitário desktop open source para Windows que exibe ao próprio usuário logado
as redes Wi-Fi salvas no computador e as respectivas senhas gravadas nos perfis locais
(equivalente ao Painel de Controle e ao comando `netsh wlan show profile <nome> key=clear`).

Segurança:
- Lê exclusivamente os perfis locais do próprio PC onde está sendo executado.
- Zero chamadas de rede, zero telemetria, zero coleta de dados.
- Senha sempre oculta por padrão até o clique explícito do usuário.
"""

from __future__ import annotations

import argparse
import ctypes
import sys
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Dict, List, Optional

from wlan_service import (
    ProfileDetailResult,
    ProfileListResult,
    WlanService,
    WlanStatus,
)

APP_TITLE = "WiFi Key Finder by Jair Lima"
APP_VERSION = "1.0.0"
MASKED_VALUE = "•" * 16


def enable_high_dpi() -> None:
    """Ativa o suporte a telas de alta densidade (High DPI) no Windows."""
    try:
        if hasattr(ctypes, "windll") and hasattr(ctypes.windll, "shcore"):
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        elif hasattr(ctypes, "windll") and hasattr(ctypes.windll, "user32"):
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def build_demo_service() -> WlanService:
    """Cria um serviço com perfis demonstrativos locais para inspeção visual e testes de UI."""
    demo_profiles_pt = (
        "\nPerfis na interface Wi-Fi:\n\n"
        "Perfis de política de grupo (somente leitura)\n"
        "---------------------------------\n"
        "    <Nenhum>\n\n"
        "Perfis de usuários\n"
        "-------------\n"
        "    Todos os Perfis de Usuários : Casa_Fibra_5G\n"
        "    Todos os Perfis de Usuários : Café & Pão Visitantes\n"
        "    Todos os Perfis de Usuários : Aeroporto_WiFi_Aberto\n"
    ).encode("utf-8")

    details_map: Dict[str, bytes] = {
        "name=Casa_Fibra_5G": (
            "\nPerfil Casa_Fibra_5G na interface Wi-Fi:\n"
            "=======================================================================\n\n"
            "Informações do perfil\n"
            "-------------------\n"
            "    Versão                : 1\n"
            "    Tipo                   : LAN sem Fio\n"
            "    Nome                   : Casa_Fibra_5G\n\n"
            "Configurações de conectividade\n"
            "---------------------\n"
            "    Número de SSIDs        : 1\n"
            '    Nome do SSID           : "Casa_Fibra_5G"\n\n'
            "Configurações de segurança\n"
            "-----------------\n"
            "    Autenticação           : WPA2-Personal\n"
            "    Codificação            : CCMP\n"
            "    Chave de segurança     : Presente\n"
            "    Conteúdo da Chave      : Familia@2026#Segura!\n"
        ).encode("utf-8"),
        "name=Café & Pão Visitantes": (
            "\nPerfil Café & Pão Visitantes na interface Wi-Fi:\n"
            "=======================================================================\n\n"
            "Configurações de conectividade\n"
            '    Nome do SSID           : "Café & Pão Visitantes"\n'
            "Configurações de segurança\n"
            "    Autenticação           : WPA3-Personal\n"
            "    Codificação            : GCMP\n"
            "    Chave de segurança     : Presente\n"
            "    Conteúdo da Chave      : PãoDeQueijoComCafé99\n"
        ).encode("cp850"),
        "name=Aeroporto_WiFi_Aberto": (
            "\nPerfil Aeroporto_WiFi_Aberto na interface Wi-Fi:\n"
            "=======================================================================\n\n"
            "Configurações de conectividade\n"
            '    Nome do SSID           : "Aeroporto_WiFi_Aberto"\n'
            "Configurações de segurança\n"
            "    Autenticação           : Aberta\n"
            "    Codificação            : Nenhuma\n"
            "    Chave de segurança     : Ausente\n"
        ).encode("utf-8"),
    }

    def demo_runner(args: List[str]):
        if "profiles" in args:
            return 0, demo_profiles_pt, b""
        for arg in args:
            if arg.startswith("name="):
                payload = details_map.get(arg)
                if payload is not None:
                    return 0, payload, b""
                return 1, "O perfil não foi encontrado no sistema.".encode("utf-8"), b""
        return 1, b"Comando desconhecido", b""

    return WlanService(runner=demo_runner, netsh_path="netsh.exe")


class WifiKeyFinderApp:
    """Interface gráfica principal do WiFi Key Finder by Jair Lima."""

    def __init__(self, root: tk.Tk, service: Optional[WlanService] = None) -> None:
        self.root = root
        self.service = service or WlanService()

        self.root.title(APP_TITLE)
        self.root.geometry("840x520")
        self.root.minsize(720, 440)
        self.root.configure(bg="#F5F7FA")

        self.all_profiles: List[str] = []
        self.filtered_profiles: List[str] = []
        self.current_detail: Optional[ProfileDetailResult] = None
        self.is_password_visible: bool = False
        self._feedback_after_id: Optional[str] = None

        self._configure_styles()
        self._build_ui()
        self._bind_shortcuts()

        # Carrega os perfis locais após inicializar a janela
        self.root.after(50, self.refresh_profiles)

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        try:
            if "vista" in style.theme_names():
                style.theme_use("vista")
            elif "clam" in style.theme_names():
                style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("Main.TFrame", background="#F5F7FA")
        style.configure("Card.TFrame", background="#FFFFFF", relief="flat")
        style.configure(
            "HeaderTitle.TLabel",
            background="#1E293B",
            foreground="#FFFFFF",
            font=("Segoe UI", 14, "bold"),
        )
        style.configure(
            "HeaderSub.TLabel",
            background="#1E293B",
            foreground="#CBD5E1",
            font=("Segoe UI", 9),
        )
        style.configure(
            "SectionTitle.TLabel",
            background="#FFFFFF",
            foreground="#0F172A",
            font=("Segoe UI", 11, "bold"),
        )
        style.configure(
            "FieldLabel.TLabel",
            background="#FFFFFF",
            foreground="#475569",
            font=("Segoe UI", 9, "bold"),
        )
        style.configure(
            "FieldValue.TLabel",
            background="#FFFFFF",
            foreground="#0F172A",
            font=("Segoe UI", 11),
        )
        style.configure(
            "Footer.TLabel",
            background="#F5F7FA",
            foreground="#64748B",
            font=("Segoe UI", 9),
        )

    def _build_ui(self) -> None:
        # Cabeçalho superior com identificação clara "by Jair Lima"
        header = tk.Frame(self.root, bg="#1E293B", padx=20, pady=12)
        header.pack(fill="x")

        title_lbl = ttk.Label(
            header,
            text=APP_TITLE,
            style="HeaderTitle.TLabel",
        )
        title_lbl.pack(anchor="w")

        sub_lbl = ttk.Label(
            header,
            text="Consulta local e segura das redes Wi-Fi e senhas salvas neste computador (100% offline)",
            style="HeaderSub.TLabel",
        )
        sub_lbl.pack(anchor="w", pady=(2, 0))

        # Corpo principal (2 colunas)
        body = ttk.Frame(self.root, style="Main.TFrame", padding=(16, 14, 16, 8))
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=2, minsize=260)
        body.columnconfigure(1, weight=3, minsize=380)
        body.rowconfigure(0, weight=1)

        # --- COLUNA ESQUERDA: Lista de Redes Salvas ---
        left_card = tk.Frame(
            body,
            bg="#FFFFFF",
            highlightbackground="#E2E8F0",
            highlightthickness=1,
            padx=14,
            pady=14,
        )
        left_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left_card.rowconfigure(2, weight=1)
        left_card.columnconfigure(0, weight=1)

        left_header = tk.Frame(left_card, bg="#FFFFFF")
        left_header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        left_header.columnconfigure(0, weight=1)

        ttk.Label(
            left_header,
            text="Redes Salvas no PC",
            style="SectionTitle.TLabel",
        ).grid(row=0, column=0, sticky="w")

        self.refresh_btn = ttk.Button(
            left_header,
            text="Atualizar (F5)",
            command=self.refresh_profiles,
        )
        self.refresh_btn.grid(row=0, column=1, sticky="e")

        # Campo de filtro rápido
        search_frame = tk.Frame(left_card, bg="#FFFFFF")
        search_frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        search_frame.columnconfigure(1, weight=1)

        tk.Label(
            search_frame,
            text="Filtrar:",
            bg="#FFFFFF",
            fg="#475569",
            font=("Segoe UI", 9),
        ).grid(row=0, column=0, padx=(0, 6))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._apply_filter())
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.grid(row=0, column=1, sticky="ew")

        # Listbox com Scrollbar
        list_container = tk.Frame(left_card, bg="#FFFFFF")
        list_container.grid(row=2, column=0, sticky="nsew")
        list_container.rowconfigure(0, weight=1)
        list_container.columnconfigure(0, weight=1)

        self.profile_listbox = tk.Listbox(
            list_container,
            font=("Segoe UI", 10),
            bg="#F8FAFC",
            fg="#0F172A",
            selectbackground="#2563EB",
            selectforeground="#FFFFFF",
            activestyle="none",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#CBD5E1",
            exportselection=False,
        )
        self.profile_listbox.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(
            list_container,
            orient="vertical",
            command=self.profile_listbox.yview,
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.profile_listbox.configure(yscrollcommand=scrollbar.set)
        self.profile_listbox.bind("<<ListboxSelect>>", self._on_profile_selected)

        self.count_label = tk.Label(
            left_card,
            text="Carregando perfis...",
            bg="#FFFFFF",
            fg="#64748B",
            font=("Segoe UI", 9),
            anchor="w",
        )
        self.count_label.grid(row=3, column=0, sticky="ew", pady=(8, 0))

        # --- COLUNA DIREITA: Detalhes e Senha ---
        right_card = tk.Frame(
            body,
            bg="#FFFFFF",
            highlightbackground="#E2E8F0",
            highlightthickness=1,
            padx=20,
            pady=18,
        )
        right_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        right_card.columnconfigure(0, weight=1)

        ttk.Label(
            right_card,
            text="Detalhes da Rede Selecionada",
            style="SectionTitle.TLabel",
        ).grid(row=0, column=0, sticky="w", pady=(0, 14))

        # Nome da Rede (SSID)
        ttk.Label(
            right_card,
            text="NOME DA REDE (SSID)",
            style="FieldLabel.TLabel",
        ).grid(row=1, column=0, sticky="w")

        self.ssid_var = tk.StringVar(value="Selecione uma rede na lista à esquerda")
        self.ssid_label = tk.Label(
            right_card,
            textvariable=self.ssid_var,
            bg="#F8FAFC",
            fg="#0F172A",
            font=("Segoe UI", 12, "bold"),
            anchor="w",
            padx=12,
            pady=8,
            highlightbackground="#E2E8F0",
            highlightthickness=1,
        )
        self.ssid_label.grid(row=2, column=0, sticky="ew", pady=(4, 14))

        # Tipo de Segurança / Autenticação
        ttk.Label(
            right_card,
            text="SEGURANÇA E AUTENTICAÇÃO",
            style="FieldLabel.TLabel",
        ).grid(row=3, column=0, sticky="w")

        self.auth_var = tk.StringVar(value="Não selecionado")
        self.auth_label = ttk.Label(
            right_card,
            textvariable=self.auth_var,
            style="FieldValue.TLabel",
        )
        self.auth_label.grid(row=4, column=0, sticky="w", pady=(2, 14))

        # Campo de Senha (sempre oculto por padrão)
        ttk.Label(
            right_card,
            text="SENHA SALVA NESTE PC",
            style="FieldLabel.TLabel",
        ).grid(row=5, column=0, sticky="w")

        pwd_box = tk.Frame(
            right_card,
            bg="#F8FAFC",
            highlightbackground="#CBD5E1",
            highlightthickness=1,
            padx=12,
            pady=10,
        )
        pwd_box.grid(row=6, column=0, sticky="ew", pady=(4, 10))
        pwd_box.columnconfigure(0, weight=1)

        self.password_display_var = tk.StringVar(value="Nenhuma rede selecionada")
        self.password_display_label = tk.Label(
            pwd_box,
            textvariable=self.password_display_var,
            bg="#F8FAFC",
            fg="#334155",
            font=("Consolas", 12, "bold"),
            anchor="w",
        )
        self.password_display_label.grid(row=0, column=0, sticky="ew")

        # Botões de ação (Mostrar/Ocultar e Copiar Senha)
        btn_row = tk.Frame(right_card, bg="#FFFFFF")
        btn_row.grid(row=7, column=0, sticky="ew", pady=(4, 12))

        self.toggle_pwd_btn = ttk.Button(
            btn_row,
            text="Mostrar senha",
            command=self.toggle_password_visibility,
            state="disabled",
            width=18,
        )
        self.toggle_pwd_btn.pack(side="left", padx=(0, 10))

        self.copy_pwd_btn = ttk.Button(
            btn_row,
            text="Copiar senha",
            command=self.copy_password,
            state="disabled",
            width=18,
        )
        self.copy_pwd_btn.pack(side="left")

        # Banner de status / diagnóstico amigável
        self.status_banner = tk.Label(
            right_card,
            text="Escolha uma rede Wi-Fi à esquerda para consultar a senha gravada no Windows.",
            bg="#EFF6FF",
            fg="#1E3A8A",
            font=("Segoe UI", 9),
            justify="left",
            anchor="w",
            wraplength=420,
            padx=12,
            pady=10,
            highlightbackground="#BFDBFE",
            highlightthickness=1,
        )
        self.status_banner.grid(row=8, column=0, sticky="ew", pady=(8, 0))

        # Rodapé com assinatura by Jair Lima e aviso de execução 100% local
        footer = ttk.Frame(self.root, style="Main.TFrame", padding=(16, 4, 16, 10))
        footer.pack(fill="x")

        ttk.Label(
            footer,
            text=f"{APP_TITLE} v{APP_VERSION} • Execução 100% local (sem uso de internet ou telemetria)",
            style="Footer.TLabel",
        ).pack(side="left")

    def _bind_shortcuts(self) -> None:
        self.root.bind("<F5>", lambda _e: self.refresh_profiles())
        self.root.bind("<Control-c>", self._on_ctrl_c)

    def _on_ctrl_c(self, _event: tk.Event) -> None:
        # Só copia a senha se o foco não estiver no campo de busca de texto
        if self.root.focus_get() != self.search_entry:
            if self.current_detail and self.current_detail.password:
                self.copy_password()

    def _set_banner(self, text: str, level: str = "info") -> None:
        palettes = {
            "info": ("#EFF6FF", "#1E3A8A", "#BFDBFE"),
            "success": ("#F0FDF4", "#166534", "#BBF7D0"),
            "warning": ("#FFFBEB", "#92400E", "#FDE68A"),
            "error": ("#FEF2F2", "#991B1B", "#FECACA"),
        }
        bg, fg, border = palettes.get(level, palettes["info"])
        self.status_banner.configure(
            text=text,
            bg=bg,
            fg=fg,
            highlightbackground=border,
        )

    def refresh_profiles(self) -> None:
        """Recarrega a lista de perfis Wi-Fi salvos no Windows."""
        self._reset_detail_panel()
        self.count_label.configure(text="Consultando perfis do Windows...")
        self.root.update_idletasks()

        result: ProfileListResult = self.service.list_profiles()
        self.all_profiles = list(result.profiles)
        self._apply_filter()

        if result.status == WlanStatus.SUCCESS:
            total = len(self.all_profiles)
            self.count_label.configure(text=f"{total} rede(s) salva(s) encontrada(s)")
            self._set_banner(
                "Selecione uma rede na lista à esquerda. Por segurança, a senha permanece oculta até que você clique em 'Mostrar senha'.",
                level="info",
            )
            if self.filtered_profiles:
                self.profile_listbox.selection_set(0)
                self._on_profile_selected()
        elif result.status == WlanStatus.NO_PROFILES:
            self.count_label.configure(text="0 redes salvas")
            self.ssid_var.set("Nenhuma rede salva encontrada")
            self.auth_var.set("Sem perfis Wi-Fi registrados")
            self.password_display_var.set("Sem senha disponível")
            self._set_banner(result.message, level="warning")
        elif result.status == WlanStatus.NO_INTERFACE_OR_SERVICE:
            self.count_label.configure(text="Sem adaptador Wi-Fi ativo")
            self.ssid_var.set("Interface Wi-Fi não encontrada")
            self.auth_var.set("Adaptador ausente ou serviço wlansvc parado")
            self.password_display_var.set("Indisponível neste PC")
            self._set_banner(result.message, level="warning")
        elif result.status == WlanStatus.PERMISSION_DENIED:
            self.count_label.configure(text="Permissão negada")
            self.ssid_var.set("Permissão negada pelo Windows")
            self.auth_var.set("Acesso restrito")
            self.password_display_var.set("Bloqueado")
            self._set_banner(result.message, level="error")
        else:
            self.count_label.configure(text="Erro ao consultar redes")
            self.ssid_var.set("Erro na leitura de perfis")
            self.auth_var.set("Verifique o serviço de rede do Windows")
            self.password_display_var.set("Erro")
            self._set_banner(result.message, level="error")

    def _apply_filter(self) -> None:
        query = self.search_var.get().strip().lower()
        if query:
            self.filtered_profiles = [
                p for p in self.all_profiles if query in p.lower()
            ]
        else:
            self.filtered_profiles = list(self.all_profiles)

        self.profile_listbox.delete(0, tk.END)
        for name in self.filtered_profiles:
            self.profile_listbox.insert(tk.END, name)

        if self.all_profiles:
            self.count_label.configure(
                text=f"Exibindo {len(self.filtered_profiles)} de {len(self.all_profiles)} rede(s)"
            )

    def _reset_detail_panel(self) -> None:
        """Restaura o painel direito e oculta qualquer senha visível anteriormente."""
        self.current_detail = None
        self.is_password_visible = False
        self.ssid_var.set("Selecione uma rede na lista à esquerda")
        self.auth_var.set("Não selecionado")
        self.password_display_var.set("Nenhuma rede selecionada")
        self.password_display_label.configure(fg="#64748B")
        self.toggle_pwd_btn.configure(text="Mostrar senha", state="disabled")
        self.copy_pwd_btn.configure(text="Copiar senha", state="disabled")

    def _on_profile_selected(self, _event: Optional[tk.Event] = None) -> None:
        selection = self.profile_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        if index < 0 or index >= len(self.filtered_profiles):
            return

        profile_name = self.filtered_profiles[index]
        self.load_profile_details(profile_name)

    def load_profile_details(self, profile_name: str) -> None:
        """Consulta os detalhes de uma rede garantindo que a senha comece SEMPRE oculta."""
        self.is_password_visible = False
        self.toggle_pwd_btn.configure(text="Mostrar senha")

        detail = self.service.get_profile_details(profile_name)
        self.current_detail = detail

        self.ssid_var.set(detail.ssid or profile_name)
        if detail.auth_type and detail.cipher_type and detail.cipher_type != "Não informado":
            self.auth_var.set(f"{detail.auth_type} ({detail.cipher_type})")
        else:
            self.auth_var.set(detail.auth_type or "Não informado")

        if detail.status == WlanStatus.SUCCESS and detail.password is not None:
            self.password_display_var.set(MASKED_VALUE)
            self.password_display_label.configure(fg="#0F172A")
            self.toggle_pwd_btn.configure(state="normal", text="Mostrar senha")
            self.copy_pwd_btn.configure(state="normal", text="Copiar senha")
            self._set_banner(
                "Senha encontrada no perfil local. Clique em 'Mostrar senha' para visualizar ou em 'Copiar senha' para copiar.",
                level="success",
            )
        elif detail.status == WlanStatus.NO_PASSWORD:
            self.password_display_var.set("(Sem senha salva neste perfil)")
            self.password_display_label.configure(fg="#64748B")
            self.toggle_pwd_btn.configure(state="disabled", text="Mostrar senha")
            self.copy_pwd_btn.configure(state="disabled", text="Copiar senha")
            self._set_banner(detail.message, level="warning")
        elif detail.status == WlanStatus.PERMISSION_DENIED:
            self.password_display_var.set("(Permissão negada pelo Windows)")
            self.password_display_label.configure(fg="#991B1B")
            self.toggle_pwd_btn.configure(state="disabled", text="Mostrar senha")
            self.copy_pwd_btn.configure(state="disabled", text="Copiar senha")
            self._set_banner(detail.message, level="error")
        else:
            self.password_display_var.set("(Não foi possível ler a senha)")
            self.password_display_label.configure(fg="#991B1B")
            self.toggle_pwd_btn.configure(state="disabled", text="Mostrar senha")
            self.copy_pwd_btn.configure(state="disabled", text="Copiar senha")
            self._set_banner(detail.message, level="error")

    def toggle_password_visibility(self) -> None:
        """Alterna entre mostrar e ocultar a senha da rede selecionada."""
        if not self.current_detail or self.current_detail.password is None:
            return

        self.is_password_visible = not self.is_password_visible
        if self.is_password_visible:
            self.password_display_var.set(self.current_detail.password)
            self.toggle_pwd_btn.configure(text="Ocultar senha")
        else:
            self.password_display_var.set(MASKED_VALUE)
            self.toggle_pwd_btn.configure(text="Mostrar senha")

    def copy_password(self) -> None:
        """Copia a senha da rede selecionada para a área de transferência do Windows."""
        if not self.current_detail or self.current_detail.password is None:
            return

        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.current_detail.password)
            self.root.update()
        except tk.TclError as exc:
            messagebox.showerror(
                APP_TITLE,
                f"Não foi possível copiar para a área de transferência:\n{exc}",
            )
            return

        self.copy_pwd_btn.configure(text="Copiado!")
        self._set_banner(
            f"A senha da rede '{self.current_detail.ssid}' foi copiada para a área de transferência.",
            level="success",
        )
        if self._feedback_after_id:
            try:
                self.root.after_cancel(self._feedback_after_id)
            except tk.TclError:
                pass
        self._feedback_after_id = self.root.after(
            2200, lambda: self.copy_pwd_btn.configure(text="Copiar senha")
        )


def run_cli_check(use_demo: bool = False) -> int:
    """Executa uma verificação de diagnóstico não-interativa (para testes no terminal)."""
    service = build_demo_service() if use_demo else WlanService()
    mode_label = "MODO DEMONSTRAÇÃO" if use_demo else "AMBIENTE REAL DO WINDOWS"
    print(f"=== {APP_TITLE} ({mode_label}) ===")
    res = service.list_profiles()
    print(f"Status da listagem : {res.status.value}")
    print(f"Mensagem           : {res.message}")
    print(f"Perfis encontrados : {len(res.profiles)}")
    for prof in res.profiles:
        det = service.get_profile_details(prof)
        has_pwd = "SIM (oculta no log)" if det.password else "NÃO"
        print(
            f"  - Perfil: {prof} | SSID: {det.ssid} | Autenticação: {det.auth_type} "
            f"| Status: {det.status.value} | Possui senha salva: {has_pwd}"
        )
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=f"{APP_TITLE}: visualizador local das redes Wi-Fi e senhas salvas no Windows."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Executa diagnóstico rápido no terminal e encerra.",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Inicia com perfis de demonstração em memória (útil em PCs desktop sem placa Wi-Fi).",
    )
    args = parser.parse_args(argv)

    if args.check:
        return run_cli_check(use_demo=args.demo)

    enable_high_dpi()
    root = tk.Tk()
    service = build_demo_service() if args.demo else WlanService()
    WifiKeyFinderApp(root, service=service)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
