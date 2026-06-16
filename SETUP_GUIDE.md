# セットアップガイド

このガイドは **初めてこのリポジトリを触る人** 向けのセットアップ手順です。

> 教材としての方針: **何が起きているかを理解しながら動かす** ことを優先するため、
> まずは Docker のコマンドを **手打ち** で実行する流れにしています。
> `Makefile` は便利ですが必須ではなく、慣れてからの補助手段として §7 にまとめています。

---

## 1. 前提ソフトウェアのインストール

### 1.1 Docker Desktop

backend / DB / Chroma / frontend をまとめて起動するために使います。

- macOS / Windows: https://www.docker.com/products/docker-desktop/ からダウンロードしてインストール
- Linux: お使いのディストリビューションのパッケージマネージャから Docker Engine と Compose plugin をインストール

インストール後、起動して以下が通れば OK です。

```bash
docker --version
docker compose version
```

### 1.2 Ollama (ローカル LLM)

教材初期段階のチャットは **Ollama** をローカル LLM として利用します。

- macOS / Windows / Linux: https://ollama.com/download
- 起動方法は §3 と §5 の 2 通りあります（Docker Compose 内 / ホスト OS 側）

> 後述のとおり、Ollama は **Docker Compose 内** で動かす方法と、
> **ホスト OS 側** で動かす方法のどちらでも構いません。
> GPU を持っている、または Docker の GPU 設定が面倒なら、
> 先に **ホスト OS 側で `ollama serve`** が手早いです。

### 1.3 起動確認

- Docker Desktop が起動していること（メニューバー/タスクトレイから確認）
- Ollama を使うなら、`ollama --version` がコマンドで通ること

---

## 2. リポジトリの取得と .env 作成

```bash
git clone git@github.com:PlusValueLab/rag-chat-template.git
cd rag-chat-template

# .env を作成（中身は .env.example のコピーで OK）
cp .env.example .env
```

`.env` の主な変数は `README.md` の §「.env の主な変数」を参照してください。
初期状態では編集不要ですが、§5 のように Ollama をホスト側で動かす場合は
`OLLAMA_URL` を書き換えます。

---

## 3. 起動: 手打ちコマンドで Docker Compose を立ち上げる

教材としては、**Makefile を使わず docker compose を直接叩く** ところから始めます。
各コマンドが何をしているかが一目で分かるためです。

### 3.1 バックグラウンドで全サービスを起動

```bash
docker compose up -d
```

これで以下のコンテナが立ち上がります。

| サービス名 (compose) | 用途 | ホスト側ポート |
| --- | --- | --- |
| `ollama` | ローカル LLM | 11434 |
| `chromadb` | ベクトル DB | 8001 |
| `db` | PostgreSQL | 5432 |
| `backend` | FastAPI | 8000 |
| `frontend` | Next.js | 3000 |

### 3.2 状態を確認する

```bash
docker compose ps
```

全サービスが `running` / `healthy` なら OK です。
backend は `db` / `chromadb` / `ollama` の healthcheck が通ってから起動します。

### 3.3 ブラウザでフロントを開く

http://localhost:3000

最初は会話が空っぽで「RAG Chat Template」のヒーローだけ表示されます。

---

## 4. モデル取得 (Ollama)

backend がチャットを呼び出すには、Ollama に **モデルがプルされている必要** があります。
モデルが無いと `/api/chat` は **404 Not Found** を返します（チャット送信時に
「資料に記載がありません」のような短文だけが出る、応答が空、等の症状になります）。

### 4.1 チャット用モデルを取得

```bash
docker compose exec ollama ollama pull llama3.2
```

`llama3.2` は `.env` の `OLLAMA_MODEL` で指定しているチャット用モデルです。
別モデル (`qwen2.5`, `gemma3` 等) を試したい場合は `OLLAMA_MODEL` を書き換えて
同じ名前のモデルを pull してください。

### 4.2 埋め込み用モデルを取得 (Phase 3 で使用)

```bash
docker compose exec ollama ollama pull nomic-embed-text
```

教材初期段階では使われませんが、Phase 3-1 (embedding 生成) で必要になるので
ついでに取得しておくとスムーズです。

### 4.3 取得済みモデルの確認

```bash
docker compose exec ollama ollama list
```

`llama3.2` と `nomic-embed-text` が表示されれば準備完了です。
http://localhost:3000 でメッセージを送ると、ストリームで応答が返ってきます。

---

## 5. 初回応答が遅い場合があります

ローカル LLM (Ollama) はクラウド LLM と違い、**手元の PC でモデルを実行** します。
そのため、特に初回の応答が遅くなることがあります。**「壊れた」のではなく、
モデルの準備中** であることが多いので、まず少し待ってください。

主な理由:

- **初回起動時のモデル読み込み**
  Ollama はリクエストごとにモデルをメモリに乗せます。最初の 1 回目だけ
  ロードに数十秒〜数分かかることがあります。
- **モデル未取得**
  §4 で `ollama pull` を実行していないと、`/api/chat` が 404 を返します。
  この場合は応答が来ないので、必ず `ollama list` で取得済みかを先に確認してください。
- **PC スペック / メモリ不足 / GPU の有無**
  CPU 推論だと数秒〜数十秒/トークン になることがあります。
  動作はしているのでログを眺めながら待つのが安全です。

応答の様子は §6 の `docker compose logs -f backend` でリアルタイムに見られます。

---

## 6. Ollama を Docker 外（ホスト OS）で動かす場合

Ollama は **Docker Compose 内で動かす必要は必須ではありません**。
ホスト OS 側に Ollama を入れている場合は、コンテナ側を止めてホストの
`ollama serve` を使うほうが、GPU・モデル管理が一段楽になります。

### 6.1 接続先を host.docker.internal に向ける

ホスト OS で `ollama serve` を立ち上げ、`.env` の `OLLAMA_URL` を以下に変更します。

```dotenv
# .env
OLLAMA_URL=http://host.docker.internal:11434
```

`host.docker.internal` は Docker から **ホスト OS のネットワーク** を指す
特殊ホスト名です。Docker Desktop (Mac/Windows) では標準で解決でき、
Linux の Docker でも近年は使えるようになっています
（古い Linux Docker では `--add-host=host.docker.internal:host-gateway` が
必要な場合があります）。

### 6.2 backend だけ再起動して .env を反映

`.env` を書き換えたら backend のみ再起動します。

```bash
docker compose up -d --force-recreate backend
```

### 6.3 (任意) Docker Compose の ollama サービスを止める

ホスト側 Ollama を使う場合、`docker compose` の `ollama` コンテナは
リソース節約のため止めても構いません。

```bash
docker compose stop ollama
```

`docker-compose.yml` の `ollama` サービスを編集（コメントアウト）するのは
任意です。**.env で接続先を切り替える** のがいちばん壊れにくいやり方です。

---

## 7. ログ確認とトラブルシューティング

起動後にうまく動かない / 初回応答が遅い場合は、まずログを見てください。
教材では「何が起きているかをログから読み取る」習慣をつけるのが大事です。

### 7.1 全サービスのログ

```bash
# 過去のログ全部
docker compose logs

# 追尾モード (Ctrl+C で抜ける)
docker compose logs -f
```

### 7.2 サービスを絞ってログを見る

```bash
docker compose logs -f backend     # FastAPI のリクエスト・例外
docker compose logs -f frontend    # Next.js のビルド・SSR ログ
docker compose logs -f db          # PostgreSQL の起動・接続
docker compose logs -f chromadb    # Chroma の起動・接続
docker compose logs -f ollama      # Ollama のモデルロード・推論ログ
```

### 7.3 よくある症状と確認順

- **チャット送信しても応答が来ない / 404 系のエラーがログに出る**
  → §4 のモデル取得が済んでいない可能性。`docker compose exec ollama ollama list`
- **backend が `dependency failed to start` で落ちる**
  → `db` / `chromadb` の healthcheck が通っていない。`docker compose logs db`
- **`http://localhost:3000` にアクセスしてもページが出ない**
  → `docker compose ps` で frontend が running か確認。`docker compose logs -f frontend`
- **コードを変えたのに反映されない**
  → backend は `docker compose build backend && docker compose up -d backend`
  で再ビルドする（依存追加時など）

---

## 8. 後片付け

```bash
# サービスを止める（データは残る）
docker compose down

# ボリュームごと削除（PostgreSQL / Chroma / Ollama のデータも消える）
docker compose down -v
```

開発中は `docker compose down` だけ、教材をリセットしたい時は `down -v` を使ってください。

---

## 9. 任意: Makefile を使う場合

`Makefile` には頻出コマンドのショートカットが入っており、
手打ちに慣れたあと作業を速めたいときに便利です。**ただし必須ではありません。**

| make ターゲット | 中身 |
| --- | --- |
| `make up-d` | `docker compose up -d` |
| `make down` | `docker compose down` |
| `make logs` | `docker compose logs -f` |
| `make pull` | `docker compose exec ollama ollama pull $(MODEL)` |
| `make pull-embed` | `docker compose exec ollama ollama pull $(EMBED_MODEL)` |
| `make migrate` | `docker compose exec backend alembic upgrade head` |

### 9.1 Windows で `make` を使いたい場合

Windows には標準で `make` が入っていません。`Chocolatey` 経由でのインストールが手早いです。

```powershell
# 1. Chocolatey 自体のインストール（管理者 PowerShell）
#    https://chocolatey.org/install の公式手順に従う

# 2. make をインストール
choco install make

# 3. インストール確認
make --version
```

`make: command not found` が出る場合は、PowerShell を **再起動** してから
PATH を確認してください。

### 9.2 Linux で `make` を使いたい場合

各ディストリの標準パッケージマネージャから入れられます。

```bash
# Debian / Ubuntu
sudo apt update
sudo apt install -y make

# Fedora / RHEL 系
sudo dnf install -y make

# Arch
sudo pacman -S make

# 確認
make --version
```

---

## 10. 次のステップ

セットアップが終わったら、`README.md` の冒頭「触る順番」と `ROAD_MAP.md` に
従って Phase 2-1 (ファイル取り込み) 以降の学習に進んでください。
