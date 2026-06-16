# セットアップガイド

このガイドは **初めてこのリポジトリを触る人** 向けのセットアップ手順です。

> 教材としての方針: **何が起きているかを理解しながら動かす** ことを優先するため、
> まずは Docker のコマンドを **手打ち** で実行する流れにしています。
> `Makefile` は便利ですが必須ではなく、慣れてからの補助手段として §7 にまとめています。

---

## 1. 前提ソフトウェアのインストール

### 1.1 Docker Desktop

backend / DB / Chroma / frontend をまとめて起動するために使います。

- macOS / Windows: [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/) からダウンロードしてインストール
- Linux: お使いのディストリビューションのパッケージマネージャから Docker Engine と Compose plugin をインストール

インストール後、起動して以下が通れば OK です。

```bash
docker --version
docker compose version
```

### 1.2 Ollama (ローカル LLM)　※docker内で起動するなら不要

教材初期段階のチャットは **Ollama** をローカル LLM として利用します。

- macOS / Windows / Linux: [https://ollama.com/download](https://ollama.com/download)
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

このリポジトリは **教材テンプレート** です。
自分の学習用リポジトリを `PlusValueLab/{Name}-rag` の形で新規作成し、
テンプレを「コピー元」として使う運用を想定しています。

> `{Name}` は自分の名前 / プロジェクト識別子に置き換えてください。
> 例: `taro-rag`, `pj-alpha-rag`

### 2.1 テンプレを clone する

まずはテンプレを手元にコピーします。

```bash
git clone git@github.com:PlusValueLab/rag-chat-template.git {Name}-rag
cd {Name}-rag
```

### 2.2 PlusValueLab に自分用リポジトリを新規作成する

GitHub の PlusValueLab Organization に、**空の** プライベートリポジトリ
`PlusValueLab/{Name}-rag` を作成します。

- README / .gitignore / LICENSE は **生成しない**（コミット衝突を避けるため）
- 可視性は **Private** を推奨

> 権限がない場合は Organization 管理者に作成してもらってください。

### 2.3 履歴を切り離して初期コミットし直す

テンプレ側の git 履歴は引きずらず、自分のリポジトリで **きれいな initial commit
から始める** ために `.git` を削除してから git を初期化します。

```bash
# テンプレの履歴を切り離す
rm -rf .git

# 自分のリポジトリとして初期化
git init -b main
git add .
git commit -m "chore: initial commit from rag-chat-template"

# 新規作成した自分用リポジトリを remote に設定
git remote add origin git@github.com:PlusValueLab/{Name}-rag.git
git push -u origin main
```

> Windows PowerShell の場合は `rm -rf .git` の代わりに
> `Remove-Item -Recurse -Force .git` を使ってください。

### 2.4 .env を作成する

```bash
# .env を作成（中身は .env.example のコピーで OK）
cp .env.example .env
```

`.env` の主な変数は `README.md` の §「.env の主な変数」を参照してください。
初期状態では編集不要ですが、§6 のように Ollama をホスト側で動かす場合は
`OLLAMA_URL` を有効化します。

> `.env` は `.gitignore` に入っているのでコミットされません。
> `.env.example` は残しておくと、別の環境でセットアップするときに楽です。

---

## 3. 起動: 手打ちコマンドで Docker Compose を立ち上げる

教材としては、**Makefile を使わず docker compose を直接叩く** ところから始めます。
各コマンドが何をしているかが一目で分かるためです。

### 3.1 バックグラウンドで全サービスを起動

```bash
docker compose up -d
```

これで以下のコンテナが立ち上がります。


| サービス名 (compose) | 用途         | ホスト側ポート |
| --------------- | ---------- | ------- |
| `ollama`        | ローカル LLM   | 11434   |
| `chromadb`      | ベクトル DB    | 8001    |
| `db`            | PostgreSQL | 5432    |
| `backend`       | FastAPI    | 8000    |
| `frontend`      | Next.js    | 3000    |


### 3.2 状態を確認する

```bash
docker compose ps
```

全サービスが `running` / `healthy` なら OK です。
backend は `db` / `chromadb` / `ollama` の healthcheck が通ってから起動します。

### 3.3 ブラウザでフロントを開く

[http://localhost:3000](http://localhost:3000)

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
[http://localhost:3000](http://localhost:3000) でメッセージを送ると、ストリームで応答が返ってきます。

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

### 6.1 仕組み（backend からの接続先）

`docker-compose.yml` の backend は以下のように書かれています。

```yaml
environment:
  OLLAMA_URL: ${OLLAMA_URL:-http://ollama:11434}
```

つまり `**.env` の `OLLAMA_URL` が設定されていればそれを使い、未設定なら
compose 内の `ollama` サービスを向く** 動きです。
ホスト側 Ollama に切り替える場合は、この仕組みを使って `.env` 側で
`OLLAMA_URL` を上書きします。

### 6.2 接続先を host.docker.internal に向ける

ホスト OS で `ollama serve` を立ち上げてから、`.env` の `OLLAMA_URL`
（既定ではコメントアウトされています）を以下のように有効化します。

```dotenv
# .env
OLLAMA_URL=http://host.docker.internal:11434
```

`host.docker.internal` は Docker から **ホスト OS のネットワーク** を指す
特殊ホスト名です。Docker Desktop (Mac/Windows) では標準で解決でき、
Linux の Docker でも近年は使えるようになっています
（古い Linux Docker では `--add-host=host.docker.internal:host-gateway` が
必要な場合があります）。

### 6.3 docker-compose.yml を 2 か所だけ手で編集する

ホスト OS 側 Ollama を使う場合は、`.env` を書き換えるだけでなく
`docker-compose.yml` を **2 か所だけ** 手で編集する必要があります。

理由:

1. `ollama` サービスがホスト側ポート `11434:11434` を bind するため、
  ホストの `ollama serve` と **ポート競合** して `docker compose up` が失敗する
2. `backend.depends_on.ollama` が compose 内 `ollama` の healthcheck を待つため、
  ホスト側 Ollama に切り替えても backend が起動できなくなる

そのため、以下を編集します（教材としてあえて手動編集にしています。
将来的に compose profile / override ファイルで自動化する想定です）。

```diff
   ollama:
     image: ollama/ollama:latest
-    ports:
-      - "11434:11434"
+    # ホスト OS 側 Ollama を使う場合はポート公開を外す
+    # ports:
+    #   - "11434:11434"
     volumes:
       - ollama:/root/.ollama

   backend:
     depends_on:
-      ollama:
-        condition: service_healthy
+      # ホスト OS 側 Ollama を使う場合は compose 内 ollama を待たない
       db:
         condition: service_healthy
       chromadb:
         condition: service_healthy
```

> これはリポジトリにコミットせず、各自の手元で書き換える前提です。
> （compose を毎回切り替えたい人は §6.4 の「任意」案を参照）

### 6.4 backend を再起動して .env を反映

上記編集を終えたら backend のみ再起動します。
compose の `${OLLAMA_URL:-...}` は **起動時に評価される** ため、
single restart ではなく `--force-recreate` で再生成する必要があります。

```bash
docker compose up -d --force-recreate backend
```

接続先が切り替わったかは `docker compose logs backend` で確認できます。

### 6.5 (任意) compose 内 ollama コンテナを止める

ホスト側 Ollama を使う場合、§6.3 でポート公開と依存を外していれば
compose 内 `ollama` コンテナが残っていても影響しません。
リソース節約のため止めておくと無駄が無いです。

```bash
docker compose stop ollama
```

### 6.6 (任意) override ファイルで切り替える

`docker-compose.yml` を毎回書き換えたくない場合は、override ファイルで
ホスト側 Ollama 用の差分だけ別管理する方法もあります（教材スコープ外なので
ここでは案だけ示します）。

```yaml
# compose.host-ollama.yml
services:
  ollama:
    # 起動から除外する
    profiles: ["disabled"]
  backend:
    # ollama 依存を上書きで消す（compose v2.20+ の !reset 機能）
    depends_on: !reset null
```

```bash
docker compose -f docker-compose.yml -f compose.host-ollama.yml up -d
```

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
- `**http://localhost:3000` にアクセスしてもページが出ない**
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


| make ターゲット        | 中身                                                      |
| ----------------- | ------------------------------------------------------- |
| `make up-d`       | `docker compose up -d`                                  |
| `make down`       | `docker compose down`                                   |
| `make logs`       | `docker compose logs -f`                                |
| `make pull`       | `docker compose exec ollama ollama pull $(MODEL)`       |
| `make pull-embed` | `docker compose exec ollama ollama pull $(EMBED_MODEL)` |
| `make migrate`    | `docker compose exec backend alembic upgrade head`      |


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