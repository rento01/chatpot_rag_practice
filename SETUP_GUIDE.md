# セットアップガイド

このガイドは **初めてこのリポジトリを触る人** 向けのセットアップ手順です。

> 教材としての方針: **何が起きているかを理解しながら動かす** ことを優先するため、
> まずは Docker のコマンドを **手打ち** で実行する流れにしています。
> `Makefile` は便利ですが必須ではなく、慣れてからの補助手段として §9 にまとめています。

> Ollama 利用方針 (Issue #29):
> このテンプレでは **Ollama はホスト OS で起動するのを標準** にしています。
> ローカル PC のスペック制約や GPU の扱いやすさを踏まえた判断です。
> Docker Compose 内で Ollama も含めて一括起動したい場合は §6 を参照してください。

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

### 1.2 Ollama (ホスト OS にインストール)

このテンプレでは Ollama を **ホスト OS** にインストールして使うのが標準です。

- macOS / Windows / Linux: [https://ollama.com/download](https://ollama.com/download)

インストール後、コマンドで以下が通れば OK です。

```bash
ollama --version
```

> Docker Compose 内で Ollama を動かす運用も可能ですが、初期段階としては
> ホスト OS 側の方が GPU や CPU リソースをそのまま使えて応答が速い場合が多いため、
> このテンプレはホスト OS 起動を標準にしています（§6 参照）。

> Linux 環境について: `docker-compose.yml` の backend に
> `extra_hosts: ["host.docker.internal:host-gateway"]` を入れてあるので、
> Linux Docker Engine でも `host.docker.internal` から
> ホスト OS の Ollama (`localhost:11434`) に到達できます。

### 1.3 起動確認

- Docker Desktop が起動していること（メニューバー / タスクトレイから確認）
- Ollama がホスト OS でインストール済みで `ollama --version` が通ること

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

`.env` の `OLLAMA_URL` は **デフォルトでホスト OS 側 Ollama を見る** 設定
（`http://host.docker.internal:11434`）になっています。
Docker Compose 内 Ollama に切り替えたい場合のみ §6 を参照して書き換えてください。

> `.env` は `.gitignore` に入っているのでコミットされません。
> `.env.example` は残しておくと、別の環境でセットアップするときに楽です。

---

## 3. ホスト OS で Ollama を起動 + モデル取得

backend がチャットを呼び出すには、Ollama に **モデルがプルされている必要** があります。
モデルが無いと Ollama は **404 Not Found** を返します。

### 3.1 Ollama サーバを起動

```bash
ollama serve
```

> macOS / Windows の Ollama アプリ版を入れている場合は、メニューバー / タスクトレイの
> アイコンが点灯していれば自動的にサーバが立ち上がっています。改めて `ollama serve` を
> 叩く必要はありません。

### 3.2 チャット用モデルを取得

別ターミナルで以下を実行します。

```bash
ollama pull llama3.2
```

`llama3.2` は `.env` の `OLLAMA_MODEL` で指定しているチャット用モデルです。
別モデル (`qwen2.5`, `gemma3` 等) を試したい場合は `OLLAMA_MODEL` を書き換えて
同じ名前のモデルを pull してください。

### 3.3 埋め込み用モデルを取得 (Phase 3 で使用)

```bash
ollama pull nomic-embed-text
```

教材初期段階では使われませんが、Phase 3-1 (embedding 生成) で必要になるので
ついでに取得しておくとスムーズです。

### 3.4 取得済みモデルの確認

```bash
ollama list
```

`llama3.2` と `nomic-embed-text` が表示されれば準備完了です。

---

## 4. Docker Compose で残りのサービスを起動

Ollama 以外のサービス（backend / frontend / db / chromadb）を Docker Compose で起動します。
`docker-compose.yml` の `ollama` サービスはデフォルトでは **profile 化されていて起動しません**
（§6 でだけ使います）。

### 4.1 バックグラウンドで起動

```bash
docker compose up -d
```

これで以下のコンテナが立ち上がります。

| サービス名 (compose) | 用途         | ホスト側ポート |
| --------------- | ---------- | ------- |
| `chromadb`      | ベクトル DB    | 8001    |
| `db`            | PostgreSQL | 5432    |
| `backend`       | FastAPI    | 8000    |
| `frontend`      | Next.js    | 3000    |

backend は環境変数 `OLLAMA_URL=http://host.docker.internal:11434` を通して
**ホスト OS 側の Ollama** に接続します。

### 4.2 状態を確認する

```bash
docker compose ps
```

全サービスが `running` / `healthy` なら OK です。

### 4.3 ブラウザでフロントを開く

[http://localhost:3000](http://localhost:3000)

最初は会話が空っぽで「RAG Chat Template」のヒーローだけ表示されます。
メッセージを送るとストリームで応答が返ってきます。

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
  §3 で `ollama pull` を実行していないと、`/api/chat` が 404 を返します。
  この場合は応答が来ないので、必ず `ollama list` で取得済みかを先に確認してください。
- **PC スペック / メモリ不足 / GPU の有無**
  CPU 推論だと数秒〜数十秒/トークン になることがあります。
  動作はしているのでログを眺めながら待つのが安全です。

応答の様子は §7 の `docker compose logs -f backend` でリアルタイムに見られます。

---

## 6. (補助) Docker Compose 内で Ollama も一括起動する場合

ホスト OS への Ollama インストールを避けたい場合や、いつものターミナル一発で
すべて立ち上げたい場合は、Docker Compose 内の `ollama` サービスを使う運用もできます。

### 6.1 仕組み (profile 化)

`docker-compose.yml` の `ollama` サービスには `profiles: ["bundled-ollama"]`
が付与されており、**通常の `docker compose up -d` では起動しません**。
`--profile bundled-ollama` を付けて起動すると、ollama も含めて全サービスが立ち上がります。

`Makefile` の `make up-d` がそのフローをまとめてあります。

```bash
make up-d        # docker compose --profile bundled-ollama up -d
```

### 6.2 .env を Compose 内 Ollama 接続に切り替える

`.env` の `OLLAMA_URL` を以下に変えます。

```dotenv
# .env
OLLAMA_URL=http://ollama:11434
```

> backend コンテナの中から見ると、compose 内の `ollama` サービスは
> ホスト名 `ollama` で名前解決されます。

### 6.3 モデル取得 (compose 内 Ollama)

ホスト側 `ollama pull` ではなく、compose 内コンテナでモデルを取ります。

```bash
make pull            # docker compose exec ollama ollama pull llama3.2
make pull-embed      # docker compose exec ollama ollama pull nomic-embed-text
```

### 6.4 起動方法のまとめ

| 起動方法 | Ollama の場所 | コマンド | 補足 |
| --- | --- | --- | --- |
| 標準 (推奨) | ホスト OS | `ollama serve` + `docker compose up -d` | §3 〜 §4 |
| Compose 一括 | compose 内 | `make up-d` + `.env` で `OLLAMA_URL=http://ollama:11434` | §6 |

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
# compose 内 Ollama を使っているとき (§6 の構成) のみ:
docker compose logs -f ollama
```

### 7.3 よくある症状と確認順

- **チャット送信しても応答が来ない / 404 系のエラーがログに出る**
  → ホスト OS で `ollama serve` が起動しているか確認。`ollama list` でモデルがあるか確認
- **backend が起動するが Ollama に繋がらない**
  → `.env` の `OLLAMA_URL` が `http://host.docker.internal:11434` (標準) か
  `http://ollama:11434` (§6 構成) のどちらかに合っているか確認。
  書き換えた後は `docker compose up -d --force-recreate backend` で反映
- **backend が `dependency failed to start` で落ちる**
  → `db` / `chromadb` の healthcheck が通っていない。`docker compose logs db`
- **[http://localhost:3000](http://localhost:3000) にアクセスしてもページが出ない**
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

> ホスト OS 側の Ollama サーバ (§3) は `docker compose down` では止まりません。
> 不要なら別途 `ollama` アプリを終了してください。

---

## 9. 任意: Makefile を使う場合

`Makefile` は **Docker Compose 内で Ollama も含めて一括起動する補助** として使えます。
標準のホスト OS Ollama 運用の人は使わなくて構いません。

| make ターゲット        | 中身                                                                | 用途 |
| ----------------- | ----------------------------------------------------------------- | --- |
| `make up-d`       | `docker compose --profile bundled-ollama up -d`                   | Compose 内 Ollama 含め一括起動 |
| `make down`       | `docker compose --profile bundled-ollama down`                    | 一括停止 |
| `make logs`       | `docker compose logs -f`                                          | ログ追尾 |
| `make pull`       | `docker compose exec ollama ollama pull $(MODEL)`                 | Compose 内 Ollama にモデル取得 |
| `make pull-embed` | `docker compose exec ollama ollama pull $(EMBED_MODEL)`           | 同上 (埋め込みモデル) |
| `make migrate`    | `docker compose exec backend alembic upgrade head`                | alembic マイグレーション |

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
