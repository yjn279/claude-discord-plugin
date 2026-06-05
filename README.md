# claude-discord-plugin

公式 Discord プラグイン（ `anthropics/claude-plugins-official` の `external_plugins/discord` ）を `git subtree` で `discord/` 配下に取り込み、メンション運用向けに3点だけ拡張したダウンストリーム・フォークである。リポジトリ自身がマーケットプレイス兼プラグインを兼ね、上流の更新は `git subtree pull` で取り込める。

## Behavior

公式プラグインからの差分は次の3点である。いずれも `access.json` のフラグで無効化できる。

| 挙動 | 内容 | 制御フラグ（既定値） |
| :-- | :-- | :-- |
| 全チャンネル反応 | `groups` に未登録のチャンネルでも、メンションされれば反応する。反応範囲は `allowFrom` （オーナー）に限定される。許可リストが空の間は安全側に倒し、opt-in 済みチャンネルのみ反応する。 | `listenAllChannels` （ `true` ） |
| スレッド自動生成 | トップレベルのチャンネルでメンションされると、その元メッセージからスレッドを生成し、返信はスレッド内に送る。 | `autoThread` （ `true` ） |
| スレッド内継続 | ボット自身が開いたスレッド内では、メンションが無くても会話に反応し続ける。人間が作った無関係なスレッドには反応しない。 | （ `autoThread` に追従） |

公式プラグインの状態ディレクトリ（ `~/.claude/channels/discord/` ）とアクセス制御スキルはそのまま流用する。トークンと許可リストは既存設定を引き継げる。

## Structure

リポジトリは取り込んだ上流コードと自前の拡張を明確に分離する。

| パス | 役割 |
| :-- | :-- |
| `discord/` | 上流 `external_plugins/discord` の subtree。プラグイン本体。 |
| `discord/server.ts` | 改修は `// discord-threads:` マーカー付きの3箇所のみ。 |
| `.claude-plugin/marketplace.json` | このリポジトリをマーケットプレイスとして登録する定義。 |
| `scripts/pull-upstream.sh` | 上流 subtree を再取得する追従スクリプト。 |
| `scripts/run-channel.sh` | チャネルを常駐起動する自動再起動ループ。 |
| `scripts/confirm-loop.py` | claude に PTY を供給し起動時プロンプトに自動応答する補助。 |

## Install

インストールは Claude Code の CLI で行う。マーケットプレイスを登録してプラグインを導入すると、`~/.claude/settings.json` の `extraKnownMarketplaces` と `enabledPlugins` が自動で更新される。

```shell
claude plugin marketplace add yjn279/claude-discord-plugin
claude plugin install discord@claude-discord-plugin
```

手動で設定する場合は `~/.claude/settings.json` の既存マップへ次を追記する。`enabledPlugins` と `extraKnownMarketplaces` は `settings.local.json` だと確実にマージされない既知の挙動があるため、本体へ書く。公式 `discord` プラグインを併用すると二重応答になるため、`discord@claude-plugins-official` は `false` にして切り替える。

```json
{
  "extraKnownMarketplaces": {
    "claude-discord-plugin": {
      "source": { "source": "github", "repo": "yjn279/claude-discord-plugin", "ref": "main" }
    }
  },
  "enabledPlugins": {
    "discord@claude-discord-plugin": true
  }
}
```

## Run

起動経路には制約がある。Claude Code の `--channels` は Anthropic が審査した承認チャネルの allowlist 限定で、自作フォークは `not on the approved channels allowlist` と拒否される（MCP は起動してもメッセージが Claude に注入されず無応答になる）。自作・フォークのチャネルを動かす正規の経路は `--dangerously-load-development-channels` であり、`plugin:` 指定でインストール済みのビルドを起動する。

```shell
claude --dangerously-load-development-channels plugin:discord@claude-discord-plugin
```

常駐させる場合は同梱の `scripts/run-channel.sh` を使う。claude は標準出力が端末でないと `--print` モードに落ちて即終了するため、`scripts/confirm-loop.py` が擬似端末（PTY）を供給し、起動時の確認プロンプトにも自動で応答する。`screen` でデタッチして常駐させ、クラッシュ時は自動再起動する。

```shell
screen -dmS discord ./scripts/run-channel.sh
```

接続確認は `screen -r discord` 、停止は `screen -S discord -X quit` で行う。

## Requirements

スレッド自動生成のため、Discord 側でボットのロールに次の権限を付与する必要がある。

| 権限 | 用途 |
| :-- | :-- |
| Create Public Threads | メンション元メッセージからのスレッド生成 |
| Send Messages in Threads | 生成したスレッド内への返信 |

`View Channel` 、 `Read Message History` 、 `Message Content Intent` は公式プラグインと同様に必要である。権限が不足してスレッド生成に失敗した場合は、チャンネルへ直接返信するフォールバックが働く。

## Upstream Sync

上流の `external_plugins/discord` に変更が入ったら、付属スクリプトで取り込む。上流を再 split し、 `discord/` subtree へ squash マージする。

```shell
./scripts/pull-upstream.sh
```

競合は改修箇所（ `discord/server.ts` の `// discord-threads:` マーカー付近、および `plugin.json` ）に限られる。解消後に `git push` で反映する。 `git subtree` の split は機械ごとに決定的なため、リポジトリを作成した同じ環境で実行する。

## License

上流と同じく Apache-2.0 である。改変箇所はすべて `// discord-threads:` コメントで明示している。
