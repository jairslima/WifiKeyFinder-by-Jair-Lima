# WiFi Key Finder by Jair Lima

## Nome e Descrição
**WiFi Key Finder by Jair Lima** é um utilitário desktop open source para Windows que exibe ao próprio usuário logado as redes Wi-Fi salvas no computador e as respectivas senhas gravadas nos perfis locais do Windows (equivalente ao que o Painel de Controle e o comando nativo `netsh wlan show profile <nome> key=clear` já mostram, porém em uma interface gráfica simples, limpa e acessível).

É uma ferramenta estritamente de conveniência para usuários que têm dificuldade de localizar essa informação na interface nativa do Windows.

## Escopo e Limites de Segurança (Invioláveis)
1. **Apenas perfis locais do próprio PC:** Lê exclusivamente os perfis de Wi-Fi salvos no computador onde está sendo executado, utilizando a utilidade nativa `netsh.exe` com as mesmas permissões que o usuário logado já possui. Não captura, não monitora, não escuta pacotes e jamais ataca redes de terceiros ou outras máquinas.
2. **Zero chamadas de rede:** Não realiza conexões HTTP, sockets, DNS nem qualquer comunicação externa. Nenhuma senha ou nome de rede é enviado para servidores, APIs, serviços de telemetria ou analytics.
3. **Sem coleta oculta ou backdoors:** Todo o processamento ocorre em memória local e é exibido unicamente na tela para o usuário logado, com a senha oculta por padrão até que o usuário clique explicitamente em revelar ou copiar.

## Stack Escolhida e Justificativa
- **Linguagem:** Python 3.10+ (desenvolvido e validado em Python 3.14)
- **Interface Gráfica:** `tkinter` / `ttk` (biblioteca padrão do Python)
- **Testes Automatizados:** `unittest` (biblioteca padrão) / `pytest`
- **Empacotamento:** `PyInstaller` (`--onefile --windowed`)

**Justificativa da escolha:**
Escolheu-se **Python com Tkinter** (sem dependências externas de tempo de execução) pelos seguintes motivos técnicos e de segurança:
1. **Superfície de ataque zero em dependências (Supply Chain Security):** Por utilizar apenas a biblioteca padrão do Python (`tkinter`, `subprocess`, `re`, `ctypes`, `os`), não há pacotes de terceiros no `requirements.txt` que possam introduzir vulnerabilidades ou telemetria indesejada, facilitando a auditoria de código aberto e garantindo aprovação limpa no `audit-vulnerabilidades.py` (Bandit + análise estática).
2. **Simplicidade e manutenibilidade:** O código completo é conciso, legível em poucos minutos por qualquer auditor ou desenvolvedor, e compila em um executável único (`.exe`) via PyInstaller para uso imediato no Windows.

## Arquitetura
O aplicativo é dividido em duas camadas desacopladas dentro do pacote principal (facilitando testes unitários completos sem depender de hardware físico):

1. **Camada de Leitura de Perfis (`wlan_service.py`):**
   - Invoca `%SystemRoot%\System32\netsh.exe` (caminho absoluto resolvido via variável de ambiente `SystemRoot` para mitigar sequestro de PATH) através de `subprocess.run([...], shell=False, creationflags=CREATE_NO_WINDOW)`.
   - **Listagem de redes:** Executa `netsh wlan show profiles` e extrai os nomes dos perfis (suportando Windows em Português, Inglês, Espanhol e outros idiomas através do parsing estruturado de linhas ` : ` na seção de perfis de usuários, além de fallback independente de idioma).
   - **Leitura de detalhes e senha:** Ao selecionar um perfil, executa `netsh wlan show profile name=<nome> key=clear` passando os argumentos como lista (nunca com `shell=True`, impedindo qualquer injeção de comando mesmo em SSIDs com caracteres especiais).
   - **Tratamento de encoding e acentuação (UTF-8 / CP850 / CP1252):** O `netsh` no Windows frequentemente emite saída na página de código OEM do console (`cp850` no Windows PT-BR) ou `utf-8`. O decodificador tenta `utf-8` estrito e faz fallback inteligente para a página de código OEM do sistema (`ctypes.windll.kernel32.GetOEMCP()`) e `cp1252`, preservando perfeitamente SSIDs e senhas com acentos (`ç`, `ã`, `é`, emojis, etc.).
   - **Classificação clara de estados e erros:**
     - `SUCCESS`: Perfil lido com senha disponível.
     - `NO_PASSWORD`: Rede aberta ou perfil corporativo/EAP ou perfil cuja senha não está salva localmente.
     - `NO_PROFILES`: Adaptador Wi-Fi ativo, mas nenhuma rede Wi-Fi salva no Windows.
     - `NO_INTERFACE_OR_SERVICE`: Serviço `wlansvc` parado ou computador sem adaptador Wi-Fi (ex.: desktop conectado apenas via cabo Ethernet).
     - `PERMISSION_DENIED`: O Windows bloqueou a leitura da chave em texto claro ou da listagem (orientando o usuário a executar com as permissões adequadas da própria conta).

2. **Camada de Interface Gráfica (`app.py`):**
   - Layout dividido em dois painéis:
     - **Esquerda:** Lista pesquisável de redes Wi-Fi salvas no PC + botão "Atualizar lista".
     - **Direita:** Painel de detalhes da rede selecionada (Nome da rede / SSID, Tipo de autenticação/segurança, Senha mascarada por padrão com `••••••••`, botão **"Mostrar senha"** / **"Ocultar senha"**, e botão **"Copiar senha"** com limpeza automática opcional ou feedback visual claro).
   - Ao trocar de rede selecionada, a senha volta automaticamente para o estado **oculto** por segurança (evitando exposição acidental na tela).
   - Identidade visual "by Jair Lima" presente nos 3 locais exigidos: título da janela, cabeçalho/rodapé visível na tela e docstring do módulo principal.

## Estrutura de Pastas
```text
WifiKeyFinder-by-Jair-Lima/
├── app.py                  # Ponto de entrada e interface gráfica (Tkinter/ttk)
├── wlan_service.py         # Serviço de leitura e parsing seguro do netsh wlan
├── tests/
│   ├── __init__.py
│   └── test_wlan_service.py # Testes unitários abrangentes (PT-BR, EN-US, UTF-8/CP850, erros)
├── LICENSE                 # Licença MIT (Copyright (c) 2026 Jair Lima)
├── README.md               # Documentação pública com seção detalhada de Segurança
├── PROJECT.md              # Plano e documentação técnica de continuidade
├── SPEC.md                 # Especificação técnica e critérios de aceite
├── GEMINI.md               # Resumo técnico para continuidade por agentes de IA
├── requirements.txt        # Vazio (apenas biblioteca padrão do Python)
└── .gitignore              # Regras de exclusão (build, dist, __pycache__, .env, *.key, etc.)
```

## Comandos de Build, Test, Run e Deploy
- **Executar aplicação:**
  ```powershell
  python app.py
  ```
- **Executar diagnósticos em modo CLI (auto-teste no próprio PC):**
  ```powershell
  python app.py --check
  ```
- **Executar testes automatizados:**
  ```powershell
  python -m unittest discover -s tests -v
  ```
- **Gerar executável (Build):**
  ```powershell
  pyinstaller --onefile --windowed --name "WiFi Key Finder by Jair Lima" --clean app.py
  ```
- **Deploy local (padrão Jair Lima):**
  ```powershell
  Copy-Item "dist\WiFi Key Finder by Jair Lima.exe" "$env:USERPROFILE\bin\WiFi Key Finder by Jair Lima.exe" -Force
  ```

## Plano de Testes
1. **Testes Unitários Automatizados (`tests/test_wlan_service.py`):**
   - Extração de lista de perfis em Windows PT-BR (`Todos os Perfis de Usuários : ...`) e EN-US (`All User Profile : ...`).
   - Extração de nomes de redes contendo espaços, dois-pontos (`Rede: Casa`), acentuação (`Café & Pão 5G`) e caracteres especiais.
   - Extração de senha (`Conteúdo da Chave` / `Key Content`) quando presente.
   - Tratamento de rede aberta ou perfil sem senha salva localmente (`Conteúdo da Chave` ausente).
   - Tratamento de erro quando o serviço `wlansvc` não está rodando ou não há adaptador Wi-Fi no PC (`Não há nenhuma interface sem fio no sistema`).
   - Tratamento de permissão negada (`Elevação necessária` / `acesso negado`).
   - Decodificação resiliente de bytes em `utf-8`, `cp850` e `cp1252`.
   - Verificação estática de segurança: garantia de que `netsh.exe` é chamado com caminho absoluto do `SystemRoot` e `shell=False`.
2. **Teste Real no Ambiente Windows:**
   - Execução direta do serviço e da GUI (`python app.py --check` e inicialização real da janela) contra o sistema operacional atual, validando o comportamento real do `netsh wlan` na máquina e simulando também o carregamento de perfis na GUI.

## Plano de Autoaperfeiçoamento
Após a implementação da v1.0 e o primeiro commit/push:
1. Executar `audit-vulnerabilidades.py` e revisar qualquer alerta estático (Bandit / regex).
2. Revisar criticamente o código quanto a:
   - Segurança do caminho do executável `netsh.exe` (evitar resolução no diretório atual).
   - Comportamento da área de transferência (limpeza ou feedback visual, bloqueio do botão copiar quando não há senha).
   - Usabilidade por teclado (atalhos `Ctrl+C`, `F5` para atualizar, `Esc`, filtro de busca instantâneo).
   - Tratamento de perfis com dois-pontos (`:`) no próprio SSID.
3. Aplicar as melhorias identificadas em uma segunda rodada (v1.1) com testes adicionais e novo commit/push.

## Estado Atual e Próximos Passos
- **Estado Atual:** Em implementação inicial (Passo 1 concluído).
- **Pendências / Decisões Futuras:** Ícone personalizado (`.ico`) opcional caso o Jair deseje adicionar uma arte específica no futuro.
