# GEMINI.md: Contexto Técnico para Agentes de IA

## Visão Geral do Projeto
- **Nome:** WiFi Key Finder by Jair Lima
- **Repositório:** `https://github.com/jairslima/WifiKeyFinder-by-Jair-Lima` (Público, Open Source, Licença MIT)
- **Propósito:** Utilitário Windows local para mostrar ao próprio usuário logado os perfis Wi-Fi salvos na máquina e suas senhas gravadas, servindo como interface amigável para `netsh wlan show profile <nome> key=clear`.

## Regras Críticas para Manutenção por IAs
1. **Inviolabilidade de Segurança:** Jamais adicione chamadas de rede (`urllib`, `requests`, `socket`, `http`), telemetria, analytics ou escrita de senhas em disco/logs. Jamais implemente recursos de varredura de pacotes, captura de redes de terceiros ou acesso a outras máquinas.
2. **Execução de Subprocesso:** Sempre invoque `netsh.exe` através do caminho absoluto resolvido via `%SystemRoot%\System32\netsh.exe` e com `shell=False`.
3. **Padrão de Autoria:** Mantenha `"by Jair Lima"` no título da janela, no cabeçalho/rodapé visível da interface e na docstring do módulo principal (`app.py`).
4. **Pontuação na Documentação:** Evite travessões na documentação em português; utilize dois-pontos, vírgulas ou parênteses.

## Estrutura Técnica
- `wlan_service.py`: Contém `WlanService`, `ProfileListResult`, `ProfileDetailResult` e `WlanStatus`. Toda a lógica de parsing do `netsh` é pura e testável via injeção de runner ou métodos de parsing.
- `app.py`: Contém `WifiKeyFinderApp` (GUI Tkinter) e o modo CLI `--check`.
- `tests/test_wlan_service.py`: Testes unitários executáveis com `python -m unittest discover -s tests -v`.
