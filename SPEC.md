# Especificação Técnica: WiFi Key Finder by Jair Lima

## 1. Objetivo
Fornecer uma interface gráfica nativa e intuitiva no Windows para que o próprio usuário logado visualize as redes Wi-Fi salvas no seu computador e consulte ou copie as respectivas senhas gravadas localmente, sem precisar navegar por múltiplos submenus do Painel de Controle ou digitar comandos `netsh` no terminal.

## 2. Escopo e Restrições de Segurança
- **Apenas leitura local:** Utiliza exclusivamente `%SystemRoot%\System32\netsh.exe` com argumentos estáticos em lista (`shell=False`) e permissões do próprio usuário logado.
- **Zero conectividade externa:** Nenhuma biblioteca de rede ou chamada externa é utilizada. Os dados nunca saem da máquina nem são gravados em arquivos de log.
- **Privacidade visual (Shoulder Surfing Protection):** As senhas permanecem ocultas (`••••••••••••`) por padrão ao selecionar qualquer rede, exigindo clique explícito no botão de revelar ou copiar.

## 3. Arquitetura e Componentes
- `wlan_service.py`: Módulo responsável pela comunicação segura com o `netsh.exe`, decodificação multi-encoding (`utf-8`, OEM codepage `cp850`, `cp1252`), parsing independente e sensível a múltiplos idiomas (Português, Inglês, Espanhol) e classificação de erros (`StatusKind`).
- `app.py`: Interface gráfica em `tkinter`/`ttk` com busca rápida de redes à esquerda, exibição detalhada à direita, botões de mostrar/ocultar e copiar senha, além de modo de verificação por linha de comando (`--check`).
- `tests/test_wlan_service.py`: Suíte de testes unitários cobrindo cenários reais em PT-BR e EN-US, acentuação, redes sem senha, ausência de adaptador Wi-Fi e permissão negada.

## 4. Dependências
- Biblioteca padrão do Python 3.10+ (`tkinter`, `subprocess`, `ctypes`, `re`, `os`, `dataclasses`, `enum`, `unittest`).
- Sem dependências de terceiros em tempo de execução.
- `pyinstaller` (apenas para empacotamento opcional em `.exe`).

## 5. Critérios de Aceite
1. Listar todas as redes Wi-Fi salvas no computador na coluna da esquerda.
2. Ao selecionar uma rede, exibir o nome (SSID), tipo de autenticação e manter a senha oculta por padrão.
3. Permitir revelar/ocultar a senha e copiá-la para a área de transferência com feedback visual.
4. Exibir mensagens claras e amigáveis nos casos: rede sem senha salva, nenhuma rede salva encontrada, permissão negada, ou computador sem adaptador/serviço Wi-Fi ativo.
5. Passar em 100% dos testes unitários e na auditoria `audit-vulnerabilidades.py` com 0 alertas altos.

## 6. Instruções Operacionais
- **Executar:** `python app.py`
- **Testar:** `python -m unittest discover -s tests -v`
- **Auditar:** `python audit-vulnerabilidades.py "WifiKeyFinder-by-Jair-Lima"`
