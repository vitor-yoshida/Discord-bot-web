Crie um bot de Discord em Python usando discord.py com slash commands, organizado em módulos: um arquivo por grupo de comandos (reconhecimento com binários, reconhecimento com APIs, utilitários), mais um módulo de validação, um de formatação e um de mensagens. O bot vai rodar dentro de um container Docker e será publicado num repositório GitHub.

## Comandos

**Reconhecimento via binário externo** (executar sempre com asyncio subprocess, passando os argumentos como lista, nunca com shell=True, sempre com timeout):
- /scan alvo:<ip> → nmap, aceitando apenas perfis de scan predefinidos (ex.: rápido = -F, serviços = -sV), validando o alvo com o módulo ipaddress contra uma allowlist de redes configurável por variável de ambiente.
- /gau dominio:<domínio> → GetAllURLs (gau) para coletar endpoints de forma passiva.
- /subfinder dominio:<domínio> → subfinder (ProjectDiscovery) para enumeração de subdomínios.

**Reconhecimento via API ou biblioteca** (sem subprocess):
- /crt dominio:<domínio> → consulta o crt.sh no endpoint JSON, extrai e deduplica os subdomínios.
- /ipinfo ip:<ip> → consulta o ipinfo.io usando um token lido de variável de ambiente.
- /whois dominio:<domínio> → usa a biblioteca python-whois e devolve os campos principais organizados (registrante, datas de criação e expiração, servidores DNS).
- /dns dominio:<domínio> → usa dnspython para consultar os registros A, AAAA, MX, NS, TXT e CNAME.

**Utilitários de apoio a estudos** (processamento local, sem rede):
- /decode tipo:<base64|url|hex|jwt> valor:<texto> → decodifica o valor conforme o tipo.
- /hash algoritmo:<md5|sha1|sha256> valor:<texto> → gera o hash do valor.
- /payloads tipo:<xss|sqli> → devolve uma lista de payloads comuns de teste.

## Requisitos que valem para todos os comandos

- Validação de entrada antes de qualquer ação: domínios com biblioteca ou regex adequada, IPs com o módulo ipaddress. Entrada inválida é recusada imediatamente com mensagem clara.
- Autorização: cada comando só pode ser usado por membros com um cargo (role) configurável por variável de ambiente.
- Tratamento de erros básico e explícito para: domínio inválido, IP inválido, host inacessível, timeout atingido, API fora do ar ou com limite excedido, ferramenta não encontrada no sistema e resultado vazio. Cada caso responde com uma mensagem própria; o bot nunca falha em silêncio e nunca expõe stack traces ao usuário (erros detalhados vão apenas para o log).
- Toda resposta usa defer (interaction.response.defer) por causa do limite de 3 segundos do Discord, e depois edita a resposta com o resultado.
- Resultados formatados de forma clara e legível, usando embeds quando fizer sentido. Quando o texto passar de ~1900 caracteres, enviar como arquivo .txt anexado em vez de mensagem.
- Limite de concorrência: no máximo 2 comandos "pesados" (os que usam binário) rodando ao mesmo tempo; pedidos excedentes recebem uma mensagem avisando para tentar novamente.
- Todas as mensagens exibidas ao usuário no Discord (respostas, erros, descrições dos comandos e dos parâmetros) devem estar em português do Brasil, centralizadas no módulo de mensagens para facilitar ajustes.
- Segredos (token do bot, token do ipinfo) somente via variáveis de ambiente, nunca no código.
- Logging básico no console (comando usado, usuário, sucesso ou erro), sem registrar tokens.

## Empacotamento e repositório

- Crie um Dockerfile que instale Python, nmap, gau e subfinder, instale as dependências do bot e rode o bot como um usuário não-root.
- Crie um docker-compose.yml que leia as variáveis de um arquivo .env e reinicie o container automaticamente se ele cair.
- Crie .dockerignore e .gitignore garantindo que o .env nunca entre na imagem nem no repositório.
- Crie um .env.example com todas as variáveis necessárias (token do Discord, token do ipinfo, ID do cargo autorizado, allowlist de redes) e valores de exemplo.
- Crie um requirements.txt com as versões das dependências fixadas.

## Documentação

Gere um README em português com:
- O que o bot faz e a lista de comandos com exemplos de uso.
- Como criar a aplicação e o bot no Discord Developer Portal e convidá-lo para um servidor.
- Como configurar o .env a partir do .env.example.
- Como rodar com Docker (docker compose up) como forma principal, e sem Docker como alternativa (listando os binários que precisam estar instalados).
- Um aviso de uso responsável: usar os comandos de reconhecimento apenas em alvos próprios ou com autorização.

Comente o código de forma que alguém iniciante em programação consiga entender a estrutura e o motivo de cada decisão.