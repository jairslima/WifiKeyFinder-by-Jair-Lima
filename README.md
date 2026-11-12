# WiFi Key Finder by Jair Lima

**WiFi Key Finder by Jair Lima** é um utilitário desktop open source para Windows que exibe ao próprio usuário logado as redes Wi-Fi salvas no computador e as senhas gravadas nos perfis desse mesmo PC.

A ferramenta oferece exatamente a mesma informação que o Painel de Controle do Windows e o comando nativo `netsh wlan show profile <nome> key=clear` já mostram ao usuário, porém em uma interface gráfica simples, direta e fácil de usar. É voltada para quem tem dificuldade de localizar essa opção nos submenus da interface nativa do Windows.

---

## Segurança

A transparência e a segurança local são princípios inegociáveis deste projeto. Qualquer pessoa pode inspecionar o código-fonte (`app.py` e `wlan_service.py`, sem dependências externas) e confirmar os três pontos abaixo:

1. **Leitura restrita aos perfis locais do próprio PC:**
   A ferramenta **só lê perfis de Wi-Fi salvos no computador onde ela está sendo executada**, utilizando a utilidade oficial do Windows (`%SystemRoot%\System32\netsh.exe`) com a permissão que o próprio usuário logado já possui (equivalente ao Painel de Controle e ao `netsh`). Ela **nunca** captura pacotes, não monitora tráfego, não escaneia nem ataca redes de terceiros e jamais acessa senhas de outras máquinas.
2. **Nenhuma chamada de rede (100% Offline):**
   O aplicativo não importa bibliotecas de rede (`requests`, `urllib`, `socket`, `http`) e não realiza nenhuma conexão externa. As redes e senhas lidas **jamais** são enviadas para servidores, APIs, serviços de telemetria ou analytics. Tudo roda e permanece exclusivamente na memória local do seu computador.
3. **Sem coleta oculta, backdoors ou exposição acidental:**
   Não há qualquer backdoor, telemetria oculta, gravação em arquivos de log ou coleta de dados além do que a tela mostra ao próprio usuário. Além disso:
   - **Ocultação por padrão:** Ao selecionar uma rede, a senha permanece mascarada (`••••••••••••••••`) até que você clique explicitamente no botão **"Mostrar senha"**.
   - **Proteção da Área de Transferência:** Ao copiar uma senha, o aplicativo oferece limpeza automática da área de transferência após 30 segundos (ativada por padrão) para evitar que a senha fique exposta no `Ctrl+V`.

---

## Funcionalidades

- **Lista de redes salvas à esquerda:** Exibe todos os perfis de Wi-Fi gravados no Windows, com campo de filtro instantâneo e botão **Limpar** para localizar rapidamente o nome da rede.
- **Painel de detalhes à direita:** Mostra o nome da rede (SSID), o tipo de segurança/autenticação (ex.: WPA2-Personal, WPA3-Personal, Aberta), o modo de conexão e o estado da senha.
- **Ocultação por padrão:** A senha sempre inicia oculta e volta a ficar oculta automaticamente ao trocar de rede selecionada ou ao pressionar `Esc`.
- **Botão Mostrar / Ocultar senha:** Revela ou esconde a senha gravada com um único clique.
- **Botão Copiar senha e Copiar nome:** Copia a chave (ou o SSID) para a área de transferência do Windows com confirmação visual imediata e limpeza automática opcional após 30s.
- **Suporte completo a acentuação e múltiplos idiomas (UTF-8 / CP850 / CP1252):** Preserva corretamente nomes de redes e senhas com acentos (`ç`, `ã`, `é`), dois-pontos (`:`), espaços e caracteres especiais, funcionando em instalações do Windows em Português, Inglês, Espanhol, Francês, Alemão, Italiano e outros idiomas.
- **Atalhos de teclado:**
  - `F5`: Atualiza a lista de redes salvas.
  - `Ctrl+F`: Foca no campo de filtro.
  - `Ctrl+C`: Copia a senha da rede selecionada.
  - `Esc`: Limpa o filtro ativo ou volta a ocultar a senha caso esteja visível.
- **Mensagens de diagnóstico claras:** Informa de maneira compreensível quando uma rede é aberta (sem senha salva), quando não há redes salvas no PC, quando o computador não possui adaptador Wi-Fi ativo ou quando o Windows exige permissão adicional.

---

## Como Instalar e Usar

### Opção 1: Executar diretamente com Python (sem instalar pacotes externos)

O projeto utiliza exclusivamente a biblioteca padrão do Python (não requer `pip install` de pacotes de terceiros para rodar).

1. Certifique-se de ter o **Python 3.10+** instalado no Windows (com suporte ao `tkinter`, incluído por padrão no instalador oficial do Python para Windows).
2. Clone este repositório:
   ```powershell
   git clone https://github.com/jairslima/WifiKeyFinder-by-Jair-Lima.git
   cd WifiKeyFinder-by-Jair-Lima
   ```
3. Inicie o aplicativo:
   ```powershell
   python app.py
   ```

### Opção 2: Gerar um Executável Único (`.exe`)

Se desejar gerar um executável portátil para usar sem abrir o terminal:

```powershell
pip install pyinstaller
pyinstaller --onefile --windowed --name "WiFi Key Finder by Jair Lima" --clean app.py
```

O executável estará pronto em `dist\WiFi Key Finder by Jair Lima.exe`.

### Passo a Passo de Uso

1. Abra o **WiFi Key Finder by Jair Lima**.
2. Na lista à esquerda (**Redes Salvas no PC**), clique sobre a rede Wi-Fi desejada (você também pode digitar parte do nome no campo **Filtrar**).
3. No painel à direita (**Detalhes da Rede Selecionada**), confira o nome (SSID), o modo de conexão e o tipo de autenticação.
4. Clique em **"Mostrar senha"** para revelar a senha na tela, ou clique diretamente em **"Copiar senha"** para copiá-la para a área de transferência.
5. Pressione **F5** ou clique em **"Atualizar (F5)"** caso tenha acabado de se conectar a uma nova rede.

---

## Testes Automatizados

Para executar a suíte de testes unitários e de interface gráfica:

```powershell
python -m unittest discover -s tests -v
```

Para testar a interface gráfica em um computador desktop sem placa Wi-Fi física (usando perfis locais simulados em memória):

```powershell
python app.py --demo
```

---

## Aviso de Responsabilidade

- **Uso exclusivo no próprio computador:** Esta ferramenta foi criada unicamente para que o proprietário ou usuário legitimamente autorizado consulte as redes Wi-Fi salvas no seu próprio computador Windows. O usuário só deve executá-la em máquinas próprias ou nas quais possua autorização expressa.
- **Proteção do ambiente e do `PATH`:** Como o aplicativo invoca o utilitário nativo do sistema operacional (`%SystemRoot%\System32\netsh.exe`), o usuário é responsável por manter a integridade do seu sistema Windows, variáveis de ambiente (`SystemRoot` / `PATH`) e o controle de acesso à sua sessão de usuário.
- O software é fornecido "no estado em que se encontra" (*as is*), sob a licença MIT, sem garantias de qualquer natureza.

---

## Licença

Distribuído sob a **Licença MIT**. Consulte o arquivo [LICENSE](LICENSE) para mais informações.

Copyright (c) 2026 Jair Lima
