"""WiFi Key Finder by Jair Lima: Serviço local de leitura de perfis Wi-Fi do Windows.

Este módulo lê exclusivamente os perfis de Wi-Fi salvos no próprio computador onde está
sendo executado, utilizando a ferramenta nativa do Windows (`netsh.exe`) com as mesmas
permissões do usuário logado. Nenhuma chamada de rede ou coleta externa é realizada.
"""

from __future__ import annotations

import ctypes
from dataclasses import dataclass, field
from enum import Enum
import os
from pathlib import Path
import re
import subprocess
from typing import Callable, List, Optional, Tuple


class WlanStatus(Enum):
    """Estados possíveis ao consultar os perfis ou detalhes de uma rede Wi-Fi."""

    SUCCESS = "success"
    NO_PASSWORD = "no_saved_key"  # nosec B105
    NO_PROFILES = "no_profiles"
    NO_INTERFACE_OR_SERVICE = "no_interface_or_service"
    PERMISSION_DENIED = "permission_denied"
    PROFILE_NOT_FOUND = "profile_not_found"
    ERROR = "error"


@dataclass(frozen=True)
class ProfileListResult:
    """Resultado da listagem de perfis Wi-Fi salvos no computador."""

    status: WlanStatus
    profiles: List[str] = field(default_factory=list)
    message: str = ""
    raw_output: str = ""


@dataclass(frozen=True)
class ProfileDetailResult:
    """Detalhes de um perfil Wi-Fi específico salvo no Windows."""

    status: WlanStatus
    profile_name: str
    ssid: str = ""
    auth_type: str = ""
    cipher_type: str = ""
    password: Optional[str] = None
    message: str = ""


CommandRunner = Callable[[List[str]], Tuple[int, bytes, bytes]]


def resolve_netsh_path() -> str:
    """Resolve o caminho absoluto seguro do netsh.exe no diretório System32 do Windows."""
    system_root = os.environ.get("SystemRoot") or os.environ.get("WINDIR") or r"C:\Windows"
    candidate = Path(system_root) / "System32" / "netsh.exe"
    if candidate.is_file():
        return str(candidate)
    return "netsh.exe"


def decode_console_bytes(data: bytes, oem_encoding: Optional[str] = None) -> str:
    """Decodifica a saída em bytes do netsh preservando acentuação em PT-BR/EN-US/UTF-8.

    O `netsh.exe` em Windows pode emitir texto em UTF-8 ou na página de código OEM
    do console (como cp850 no Windows em Português ou cp437 nos EUA).
    """
    if not data:
        return ""

    # 1. Tenta UTF-8 estrito primeiro (cobre sistemas com UTF-8 global ativo ou emojis)
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        pass

    # 2. Tenta a página de código OEM nativa do Windows (ex: cp850 no Brasil)
    encodings_to_try: List[str] = []
    if oem_encoding:
        encodings_to_try.append(oem_encoding)
    else:
        try:
            if hasattr(ctypes, "windll") and hasattr(ctypes.windll, "kernel32"):
                oem_cp = ctypes.windll.kernel32.GetOEMCP()
                if oem_cp:
                    encodings_to_try.append(f"cp{oem_cp}")
                ansi_cp = ctypes.windll.kernel32.GetACP()
                if ansi_cp:
                    encodings_to_try.append(f"cp{ansi_cp}")
        except Exception:
            pass

    for fallback in ("cp850", "cp1252", "cp437"):
        if fallback not in encodings_to_try:
            encodings_to_try.append(fallback)

    for enc in encodings_to_try:
        try:
            return data.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue

    return data.decode("utf-8", errors="replace")


def default_command_runner(args: List[str]) -> Tuple[int, bytes, bytes]:
    """Executa um comando local sem abrir janela de console e sempre com shell=False."""
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    completed = subprocess.run(
        args,
        capture_output=True,
        shell=False,
        timeout=15,
        creationflags=creation_flags,
        check=False,
    )
    return completed.returncode, completed.stdout or b"", completed.stderr or b""


# Padrões de erro conhecidos em múltiplos idiomas (PT-BR, EN-US, ES)
_NO_INTERFACE_PATTERNS = (
    r"n.o h. nenhuma interface sem fio",
    r"there is no wireless interface",
    r"no hay ninguna interfaz inal.mbrica",
    r"servi.o de configura..o autom.tica sem fio.*n.o est. em execu..o",
    r"wireless autoconfig service.*is not running",
    r"wlansvc.*not running",
)

_PERMISSION_DENIED_PATTERNS = (
    r"acesso negado",
    r"access is denied",
    r"eleva..o necess.ria",
    r"requires elevation",
    r"privil.gios de administrador",
)

_PROFILE_NOT_FOUND_PATTERNS = (
    r"n.o foi encontrado no sistema",
    r"is not found on the system",
    r"no se encuentra en el sistema",
)

# Rótulos da linha de item de perfil no comando `netsh wlan show profiles`
_PROFILE_ITEM_LABELS = (
    r"todos os perfis de usu.rios",
    r"all user profile",
    r"perfil de usu.rio atual",
    r"current user profile",
    r"perfil de todos los usuarios",
    r"perfil de pol.tica de grupo",
    r"group policy profile",
)

# Rótulos conhecidos nos detalhes do perfil (`netsh wlan show profile name=X key=clear`)
_KEY_CONTENT_LABELS = (
    r"conte.do da chave",
    r"key content",
    r"contenido de la clave",
)

_SECURITY_KEY_LABELS = (
    r"chave de seguran.a",
    r"security key",
    r"clave de seguridad",
)

_AUTH_LABELS = (
    r"autentica..o",
    r"authentication",
    r"autenticaci.n",
)

_CIPHER_LABELS = (
    r"codifica..o",
    r"cifra",
    r"cipher",
    r"cifrado",
)

_SSID_NAME_LABELS = (
    r"nome do ssid",
    r"ssid name",
    r"nombre del ssid",
)

_ABSENT_VALUES = (
    "ausente",
    "absent",
    "ausentes",
    "nenhum",
    "none",
    "aberta",
    "open",
)


def _matches_any(text: str, patterns: Tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(re.search(pat, lowered) for pat in patterns)


def _split_label_value(line: str) -> Optional[Tuple[str, str]]:
    """Divide uma linha do tipo '   Rótulo   : Valor' preservando dois-pontos dentro do valor."""
    if ":" not in line:
        return None
    label, value = line.split(":", 1)
    return label.strip(), value.strip()


class WlanService:
    """Serviço responsável por listar perfis Wi-Fi do próprio PC e ler suas chaves locais."""

    def __init__(
        self,
        runner: Optional[CommandRunner] = None,
        netsh_path: Optional[str] = None,
    ) -> None:
        self._runner: CommandRunner = runner or default_command_runner
        self._netsh_path: str = netsh_path or resolve_netsh_path()

    def list_profiles(self) -> ProfileListResult:
        """Lista todos os perfis de redes Wi-Fi salvos neste computador."""
        cmd = [self._netsh_path, "wlan", "show", "profiles"]
        try:
            returncode, stdout_b, stderr_b = self._runner(cmd)
        except FileNotFoundError:
            return ProfileListResult(
                status=WlanStatus.ERROR,
                message="O utilitário nativo 'netsh.exe' do Windows não foi encontrado no sistema.",
            )
        except subprocess.TimeoutExpired:
            return ProfileListResult(
                status=WlanStatus.ERROR,
                message="A consulta ao serviço de Wi-Fi do Windows excedeu o tempo limite.",
            )
        except OSError as exc:
            return ProfileListResult(
                status=WlanStatus.ERROR,
                message=f"Erro ao executar o utilitário netsh do Windows: {exc}",
            )

        output = decode_console_bytes(stdout_b + b"\n" + stderr_b).strip()
        return self.parse_profiles_output(returncode, output)

    @staticmethod
    def parse_profiles_output(returncode: int, output: str) -> ProfileListResult:
        """Analisa o texto retornado por `netsh wlan show profiles`."""
        if _matches_any(output, _NO_INTERFACE_PATTERNS):
            return ProfileListResult(
                status=WlanStatus.NO_INTERFACE_OR_SERVICE,
                message=(
                    "Nenhuma interface Wi-Fi ativa foi encontrada neste computador "
                    "(ou o serviço 'Configuração Automática de WLAN / wlansvc' está desativado)."
                ),
                raw_output=output,
            )

        if _matches_any(output, _PERMISSION_DENIED_PATTERNS):
            return ProfileListResult(
                status=WlanStatus.PERMISSION_DENIED,
                message=(
                    "Permissão negada pelo Windows ao consultar os perfis de Wi-Fi. "
                    "Execute o aplicativo com uma conta autorizada neste computador."
                ),
                raw_output=output,
            )

        profiles: List[str] = []
        seen = set()

        for raw_line in output.splitlines():
            parsed = _split_label_value(raw_line)
            if not parsed:
                continue
            label, value = parsed
            if not value:
                continue
            if _matches_any(label, _PROFILE_ITEM_LABELS):
                if value not in seen:
                    seen.add(value)
                    profiles.append(value)

        if profiles:
            return ProfileListResult(
                status=WlanStatus.SUCCESS,
                profiles=profiles,
                message=f"{len(profiles)} rede(s) Wi-Fi salva(s) encontrada(s).",
                raw_output=output,
            )

        if returncode != 0 and output:
            return ProfileListResult(
                status=WlanStatus.ERROR,
                message=f"Não foi possível listar as redes Wi-Fi: {output.splitlines()[0]}",
                raw_output=output,
            )

        return ProfileListResult(
            status=WlanStatus.NO_PROFILES,
            profiles=[],
            message="Nenhuma rede Wi-Fi salva foi encontrada neste computador.",
            raw_output=output,
        )

    def get_profile_details(self, profile_name: str) -> ProfileDetailResult:
        """Lê os detalhes e a senha salva localmente de um perfil Wi-Fi específico."""
        clean_name = (profile_name or "").strip()
        if not clean_name or "\x00" in clean_name:
            return ProfileDetailResult(
                status=WlanStatus.ERROR,
                profile_name=clean_name,
                message="Nome de perfil Wi-Fi inválido.",
            )

        cmd = [
            self._netsh_path,
            "wlan",
            "show",
            "profile",
            f"name={clean_name}",
            "key=clear",
        ]
        try:
            returncode, stdout_b, stderr_b = self._runner(cmd)
        except FileNotFoundError:
            return ProfileDetailResult(
                status=WlanStatus.ERROR,
                profile_name=clean_name,
                message="O utilitário nativo 'netsh.exe' do Windows não foi encontrado.",
            )
        except subprocess.TimeoutExpired:
            return ProfileDetailResult(
                status=WlanStatus.ERROR,
                profile_name=clean_name,
                message="Tempo limite excedido ao consultar os detalhes da rede.",
            )
        except OSError as exc:
            return ProfileDetailResult(
                status=WlanStatus.ERROR,
                profile_name=clean_name,
                message=f"Erro ao consultar o perfil '{clean_name}': {exc}",
            )

        output = decode_console_bytes(stdout_b + b"\n" + stderr_b).strip()
        return self.parse_profile_detail_output(clean_name, returncode, output)

    @staticmethod
    def parse_profile_detail_output(
        profile_name: str, returncode: int, output: str
    ) -> ProfileDetailResult:
        """Analisa a saída de `netsh wlan show profile name=<nome> key=clear`."""
        if _matches_any(output, _NO_INTERFACE_PATTERNS):
            return ProfileDetailResult(
                status=WlanStatus.NO_INTERFACE_OR_SERVICE,
                profile_name=profile_name,
                ssid=profile_name,
                message=(
                    "Não há interface Wi-Fi ativa neste computador ou o serviço 'wlansvc' "
                    "não está em execução."
                ),
            )

        if _matches_any(output, _PERMISSION_DENIED_PATTERNS):
            return ProfileDetailResult(
                status=WlanStatus.PERMISSION_DENIED,
                profile_name=profile_name,
                ssid=profile_name,
                message=(
                    "Permissão negada pelo Windows para ler a senha desta rede. "
                    "Para revelar senhas salvas em alguns perfis do sistema, pode ser "
                    "necessário abrir o aplicativo como Administrador do próprio PC."
                ),
            )

        if _matches_any(output, _PROFILE_NOT_FOUND_PATTERNS):
            return ProfileDetailResult(
                status=WlanStatus.PROFILE_NOT_FOUND,
                profile_name=profile_name,
                ssid=profile_name,
                message=f"O perfil '{profile_name}' não foi encontrado no Windows.",
            )

        if returncode != 0:
            first_line = output.splitlines()[0] if output else "Erro desconhecido do netsh."
            return ProfileDetailResult(
                status=WlanStatus.ERROR,
                profile_name=profile_name,
                ssid=profile_name,
                message=f"Não foi possível ler os dados do perfil '{profile_name}': {first_line}",
            )

        ssid = profile_name
        auth_type = ""
        cipher_type = ""
        security_key_state = ""
        key_content: Optional[str] = None

        for raw_line in output.splitlines():
            parsed = _split_label_value(raw_line)
            if not parsed:
                continue
            label, value = parsed
            if not value:
                continue

            if _matches_any(label, _SSID_NAME_LABELS):
                cleaned_ssid = value.strip('"')
                if cleaned_ssid:
                    ssid = cleaned_ssid
            elif _matches_any(label, _AUTH_LABELS) and not auth_type:
                auth_type = value
            elif _matches_any(label, _CIPHER_LABELS) and not cipher_type:
                cipher_type = value
            elif _matches_any(label, _SECURITY_KEY_LABELS):
                security_key_state = value
            elif _matches_any(label, _KEY_CONTENT_LABELS):
                key_content = value

        if key_content is not None and key_content != "":
            return ProfileDetailResult(
                status=WlanStatus.SUCCESS,
                profile_name=profile_name,
                ssid=ssid,
                auth_type=auth_type or "WPA2/WPA3",
                cipher_type=cipher_type or "CCMP",
                password=key_content,
                message="Senha localizada com sucesso no perfil deste computador.",
            )

        # Sem Conteúdo da Chave: rede aberta, corporativa (802.1X) ou chave não armazenada/bloqueada
        key_state_lower = security_key_state.lower()
        auth_lower = auth_type.lower()

        if any(ab in key_state_lower for ab in _ABSENT_VALUES) or any(
            ab in auth_lower for ab in ("aberta", "open")
        ):
            reason = "Esta rede é aberta (sem senha) ou não possui chave de segurança."
        elif security_key_state:
            reason = (
                "A chave de segurança consta como presente no perfil, mas o Windows não "
                "retornou a senha em texto claro (pode ser rede corporativa 802.1X/EAP, "
                "senha não salva localmente ou exigir execução como Administrador local)."
            )
        else:
            reason = "Este perfil não possui uma senha salva localmente no Windows."

        return ProfileDetailResult(
            status=WlanStatus.NO_PASSWORD,
            profile_name=profile_name,
            ssid=ssid,
            auth_type=auth_type or "Não informado",
            cipher_type=cipher_type or "Não informado",
            password=None,
            message=reason,
        )
