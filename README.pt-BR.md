# Snap de inferência Qwen3 Embedding

[![qwen3-embedding](https://snapcraft.io/qwen3-embedding/badge.svg)](https://snapcraft.io/qwen3-embedding)

<!-- README-I18N:START -->

[English](./README.md) | **Português (Brasil)** | [简体中文](./README.zh-CN.md)

<!-- README-I18N:END -->

**[Qwen3-Embedding](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)** é a família de modelos de
*embedding* de texto da [equipe Qwen](https://qwen.ai), projetada para recuperação de
informação, busca semântica, pipelines de RAG, classificação, clusterização e busca de código.
Suporta mais de 100 idiomas (incluindo linguagens de programação), entradas de 32K tokens,
dimensões de saída definidas pelo usuário (Matryoshka) e instruções específicas por tarefa. A
variante 8B foi **nº 1 no ranking multilíngue do MTEB** no lançamento (junho de 2025, score
70.58).

Use este snap para instalar rapidamente um ambiente otimizado para *embedding* de texto local
com Qwen3-Embedding, servido por uma API compatível com OpenAI em `/v1/embeddings`.

O snap inclui os seguintes motores de inferência otimizados por hardware:

* cpu: Otimizado para CPUs x64 e ARM (armv8, armv9)
* nvidia-gpu: Aceleração via CUDA
* amd-gpu: aceleração por GPU com ROCm para GPUs AMD

O motor mais adequado é selecionado automaticamente com base no hardware disponível.

#### Instalação
```shell
sudo snap install qwen3-embedding
```

#### Uso
```shell
curl -s http://127.0.0.1:8362/v1/embeddings \
  -H 'Content-Type: application/json' \
  -d '{"model": "qwen3-embedding-0-6b", "input": "O que é um inference snap?"}'
```

> [!TIP]
> Alguns aceleradores exigem [drivers](https://documentation.ubuntu.com/inference-snaps/how-to/setup/drivers/) adicionais para funcionar com este snap.
> O motor `amd-gpu` usa o driver `amdgpu` do kernel (KFD); as bibliotecas de user
> space do ROCm vêm embarcadas no snap, então não é preciso instalar ROCm no host.

## Tamanhos de modelo

Três tamanhos estão disponíveis. O 0.6B é o padrão; troque com
`sudo qwen3-embedding use-model <modelo>` e reinicie o serviço:

| Modelo | Pesos | Disco (instalado) | Dimensão | Observações |
| --- | --- | --- | --- | --- |
| `qwen3-embedding-0-6b` (Q8_0) | 0,64 GB | ~1,0 GB | 1024 | Rápido, edge/RAG; quantização quase sem perdas |
| `qwen3-embedding-4b` (Q8_0) | 4,28 GB | ~4,7 GB | 2560 | Maior qualidade de recuperação |
| `qwen3-embedding-8b` (Q4_K_M) | 4,68 GB | ~5,1 GB | 4096 | Qualidade máxima (nº 1 MTEB multilíngue) |

```shell
sudo qwen3-embedding use-model qwen3-embedding-4b
sudo snap restart qwen3-embedding
```

Todos os pesos são GGUFs oficiais publicados pela equipe Qwen
([0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B-GGUF),
[4B](https://huggingface.co/Qwen/Qwen3-Embedding-4B-GGUF),
[8B](https://huggingface.co/Qwen/Qwen3-Embedding-8B-GGUF)). O 0.6B e o 4B vêm em Q8_0 (quase sem
perdas); o 8B vem em Q4_K_M porque o build oficial Q8_0 (8,05 GB) excede o limite de 5 GiB por
componente da Snap Store e exigiria *sharding* dos pesos.

## Requisitos

Medido no motor cpu como pico de RSS do `llama-server` com o runtime llama.cpp fixado. O
contexto é ajustado à memória disponível (`--fit-ctx`, piso de 4096 tokens, teto de 32K), então
o cache KV — e portanto o consumo de memória — escala com a RAM livre e o tamanho do modelo:

| Modelo | Pesos | Cache KV (4096 → 32768 tokens) | RSS total típico |
| --- | --- | --- | --- |
| 0.6B | 0,64 GB | 0,45 → 3,6 GB | ~1,4 → 4,6 GB |
| 4B | 4,28 GB | 0,60 → 4,8 GB | ~5,2 → 9,4 GB |
| 8B | 4,68 GB | 0,60 → 4,8 GB | ~5,6 → 9,8 GB |

Reserve **~110 KB por token de contexto** no 0.6B e **~147 KB por token** no 4B/8B, além dos
pesos. No motor nvidia-gpu o llama.cpp descarrega tantas camadas quanto couberem na GPU, então
*offload* parcial é suportado.

O uso de disco é de ~1,0 GB após a instalação com o modelo 0.6B (snap + componente llama.cpp +
pesos), mais ~1,1 GB se o motor nvidia-gpu for selecionado (~730 MB de download), ou ~3,8 GB se o
motor amd-gpu for selecionado (~1,1 GB de download).

## Guia de uso

### Embedding básico

```shell
curl -s http://127.0.0.1:8362/v1/embeddings -H 'Content-Type: application/json' -d '{
  "model": "qwen3-embedding-0-6b",
  "input": ["Qual é a capital da China?", "A capital da China é Pequim."]}'
```

Os vetores voltam **normalizados L2**, então o produto escalar de dois vetores é a similaridade
cosseno. A resposta segue o esquema OpenAI de embeddings (`data[].embedding`, `data[].index`,
`usage.prompt_tokens`).

### Instruções (recomendado para recuperação)

O Qwen3-Embedding entende instruções: prefixar **consultas** com a descrição da tarefa melhora a
recuperação em ~1-5% (medição do fabricante; nossa bateria E2E mostra margem maior em exemplos
pequenos). Documentos são embutidos como estão:

```shell
INSTRUCT="Instruct: Given a web search query, retrieve relevant passages that answer the query\nQuery: "
curl -s http://127.0.0.1:8362/v1/embeddings -H 'Content-Type: application/json' -d "{
  \"model\": \"qwen3-embedding-0-6b\",
  \"input\": \"${INSTRUCT}Como funciona um snap do Ubuntu?\"}"
```

Escreva instruções em **inglês** mesmo para conteúdo em outros idiomas: a maioria das instruções
de treino era em inglês. Adicione a instrução apenas no lado da consulta — adicioná-la aos
documentos piora o resultado.

### Dimensões personalizadas (Matryoshka)

Os modelos suportam Matryoshka Representation Learning: as primeiras *N* dimensões do vetor
permanecem significativas após truncamento + renormalização (0.6B: 32-1024, 4B: até 2560, 8B:
até 4096). O servidor sempre retorna o vetor completo, então trunque no cliente:

```python
import math
v = response["data"][0]["embedding"][:256]
v = [x / math.sqrt(sum(t*t for t in v)) for x in v]   # renormalize após truncar
```

O parâmetro `dimensions` da OpenAI é aceito mas **ignorado** pelo llama-server embutido (ele
sempre retorna a dimensão completa); faça o truncamento acima no cliente.

### Documentos longos e lotes

* Entradas maiores que o contexto ajustado são rejeitadas com HTTP 400
  (`exceed_context_size_error`) em vez de truncadas silenciosamente — fatie seus documentos (o
  ponto ideal do modelo são passagens de até alguns milhares de tokens).
* Uma única requisição pode embutir uma lista de textos; mantenha o **total** de tokens do lote
  dentro do contexto, ou divida em várias requisições.

## Configuração

O motor lê suas configurações da configuração do snap:

| Configuração | Padrão | Propósito |
| --- | --- | --- |
| `min-context-size` | `4096` | Piso do `--fit-ctx`; o `--fit` cresce o contexto até o limite de 32K do modelo |
| `sleep-idle-seconds` | `600` | Tempo ocioso antes de o `llama-server` descarregar o modelo (libera RAM) |
| `ubatch-size` | `512` | Lote físico de processamento de prompt (throughput × RAM) |
| `http.port` / `http.host` | `8362` / `127.0.0.1` | API compatível com OpenAI |
| `verbose` | `false` | Passa `--verbose` ao `llama-server` |

Leia com `qwen3-embedding get`; alterá-las exige root (`sudo qwen3-embedding set`) e o serviço
precisa ser reiniciado para aplicar:

```shell
qwen3-embedding get
sudo qwen3-embedding set ubatch-size=8192
sudo snap restart qwen3-embedding
```

`ubatch-size=8192` é o valor recomendado pelo fabricante para throughput máximo de embedding;
custa um *compute buffer* maior (RAM/VRAM). O padrão 2048 é o ponto ideal medido para chunks
típicos de RAG em CPU.

## Recursos

📚 **[Documentação](https://documentation.ubuntu.com/inference-snaps/)**, aprenda a usar inference snaps

🤗 **[Model card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)**, documentação oficial do modelo

📦 **[Pesos GGUF](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B-GGUF)**, os pesos quantizados que este snap embute

🧩 **[Repositório Qwen3-Embedding](https://github.com/QwenLM/Qwen3-Embedding)**, código de avaliação e exemplos de uso

📝 **[Relatório técnico](https://arxiv.org/pdf/2506.05176)**, Qwen3 Embedding: Multilingual, Versatile, Efficient

🐛 **[Issues](https://github.com/amenezes/qwen3embedding-snap/issues)**, reporte bugs e peça recursos

## Notas sobre este snap

* **Pin de runtime:** o llama.cpp está fixado em `b10344`, o build também usado pelos snaps
  irmãos (`minicpm5-2b`, `qwen3guard`) e pelos snaps `phi4`/`smollm2`/`gemma4` da Canonical. O
  suporte à arquitetura Qwen3 (incluindo os modelos de embedding) chegou ao upstream em maio de
  2025, bem antes deste pin. Atualizações chegam como PRs revisados do Renovate (nunca
  automerge) e precisam passar na bateria E2E de embeddings (`make embed-test`).
* **Pooling:** o motor passa `--pooling last` explicitamente — o *pooling* de último token (EOS)
  com o qual o Qwen3-Embedding foi treinado. Os GGUFs oficiais embutem o mesmo valor nos
  metadados (`llama.pooling_type=LAST`); a flag mantém funcionando GGUFs requantizados que
  perdem esse metadado.
* **Sem web UI:** este snap não traz interface de chat nem webui — modelos de embedding produzem
  vetores, não texto. O `llama-server` embutido ainda responde `/v1/chat/completions` com saída
  sem sentido (é um modelo base); use `/v1/embeddings`.
* **Normalização:** os vetores são normalizados L2 no servidor (padrão do `--embd-normalize` do
  llama.cpp), compatível com o uso pretendido de similaridade cosseno.
* **Licença do modelo:** Apache-2.0 (equipe Qwen, Alibaba Group). O código de empacotamento é
  GPL-3.0.
* **Seleção de motor:** os motores `nvidia-gpu` e `amd-gpu` são escolhidos sempre que
  existe uma GPU do fornecedor correspondente no barramento PCI, mesmo que o driver não
  esteja utilizável. Nesse caso o backend falha ao inicializar e o llama.cpp cai para o
  backend de CPU; rode `sudo qwen3-embedding use-engine cpu` para voltar e liberar o
  componente do motor (~1,1 GB no NVIDIA, ~3,8 GB no AMD). O motor AMD só casa as
  microarquiteturas suportadas pelo build ROCm embarcado (gfx1010–gfx1201, incluindo a
  RX 9070 XT); GPUs AMD mais antigas selecionam o motor cpu. A seleção roda na instalação e
  precisa da interface `hardware-observe`; se a auto-conexão não tiver sido concedida,
  conecte e rode a seleção manualmente:
  ```shell
  sudo snap connect qwen3-embedding:hardware-observe
  sudo qwen3-embedding use-engine --auto
  ```
* **O motor AMD precisa de `process-control`:** o runtime ROCm fixa suas threads de trabalho com
  `sched_setaffinity`, e a política seccomp padrão do snapd só permite essa chamada para o pid 0.
  Sem o plugue, o HSA falha ao inicializar, o llama.cpp registra `no ROCm-capable device is
  detected` e roda na CPU enquanto o motor continua aparecendo como `amd-gpu`. A interface não é
  auto-conectada, então conecte-a uma vez após a instalação — e peça a auto-conexão antes de
  publicar na loja:
  ```shell
  sudo snap connect qwen3-embedding:process-control
  sudo snap restart qwen3-embedding.server
  ```
* **Provider:** o snap exporta um slot de conteúdo `inference-provider`, para que outro snap
  possa consumir este endpoint em vez de rodar o próprio modelo.
* **API local:** o endpoint não tem autenticação e permite requisições de outras origens. Ele
  escuta apenas em `127.0.0.1` — não rebinda `http.host` para uma interface pública.
* **Porta:** 8362 continua a sequência da família inference-snaps (8324-8361 são usadas pelos
  snaps da Canonical, 8364/8365 pelo snap irmão `qwen3guard`).

## Compilar e instalar a partir do código

Clone o repositório:
```shell
git clone <este-repo>
```

Inicialize o ambiente de desenvolvimento:
```shell
make init        # pesos padrão 0.6B (~0,6 GB) + verificação de checksum
make init-all    # os três tamanhos (~9,6 GB)
```

O `snapcraft` compila dentro de um contêiner por padrão, então um provider de build precisa
estar disponível. Com LXD, inicialize uma vez (`--storage-backend=dir` evita um pool ZFS em
loop):

```shell
lxd init --auto --storage-backend=dir
```

Sem provider, compile no host com `sudo snapcraft pack --destructive-mode --platform amd64`.

Compile e instale o snap:
```shell
make build       # requer init-all: os três GGUFs viram componentes
make install
```

Valide o servidor em execução com a bateria E2E de embeddings:
```shell
make embed-test                       # contra o snap instalado (porta 8362)
make embed-test MODEL=qwen3-embedding-4b DIM=2560
```

Para usar cópias locais dos pesos, coloque-as em `components/model-*-gguf/` e rode
`make verify-model` / `make verify-extra-models`; as variáveis `GGUF_*` do `Makefile` são
sobrescrevíveis para espelhos internos.

## Publicação na Snap Store

Dois pedidos do lado da loja são pré-requisitos e ambos demoram, então abra-os cedo:

* **Acesso a upload de componentes** — os pesos e o runtime llama.cpp são distribuídos como
  [components](https://snapcraft.io/docs/explanation/how-snaps-work/snap-components/) e o upload
  de componentes é limitado a contas na allow-list da loja. Peça no
  [fórum do Snapcraft](https://forum.snapcraft.io/c/store-requests/).
* **Auto-conexão de `hardware-observe`** — a interface não é auto-conectada por padrão, então uma
  instalação pela loja não detecta o hardware no `use-engine --auto` até o pedido ser concedido
  (veja o
  [processo](https://snapcraft.io/docs/reference/administration/process-for-aliases-auto-connections-and-tracks/)).

O primeiro upload também exige um nome registrado e um repositório que exista de fato: a página
da loja liga `website`, `source-code`, `issues` e `contact` do `snap/snapcraft.yaml`.

```shell
snapcraft login
snapcraft register qwen3-embedding
make build
./dev/upload.sh latest/edge   # snapcraft upload <snap> --component ... --release=latest/edge
```

`.github/workflows/cicd.yaml` publica em `latest/edge` a cada push na `main` assim que o secret
`SNAPCRAFT_STORE_CREDENTIALS` (saída de `snapcraft export-login`) estiver configurado. Note que
o runner de CI precisa de ~25 GB livres: o `make init-all` baixa os três GGUFs porque o build os
organiza em componentes.
