# 设置、清理与更新

SKILL.md 第 0 节把你送来时读本文件。

当本次调用的参数（见 SKILL.md 第 0 节）以 `config` 开头时（例如 `/answer-me-with-html config open off`），本轮只处理设置，不产出页面：

- `config`：运行 `am config` 显示当前设置，然后让用户选择。agent 有选择工具（如 AskUserQuestion）时用它：一次最多 4 项设置，优先这几项：`open`、`theme`、`mode`、`style`，选项里标出当前值。否则用纯文字询问。
- `config <key> <value>`：运行 `am config set <key> <value>`。
- `config reset [key]`：运行 `am config reset [key]`。

当用户用自然语言提出要求时（「别再自动打开浏览器了」「默认用卡片主题」），也转换成 `am config set`。设置项：`open`（自动打开浏览器）、`theme`、`mode`、`style`、`voice`（视频配音）、`update_check`（新版本提示）、`close_after_reply`（复制回复后关闭页面标签页）。运行 `am config` 查看全部说明。

`update_check` 会让 CLI 每天最多一次从 GitHub 仓库的 `main` 分支下载 `package.json` 和 `highlights.json`（raw.githubusercontent.com）；它不发送任何关于用户或其页面的信息，也从不安装任何东西。要关掉它，运行 `am config set update_check false`，或设置 `AM_NO_UPDATE_CHECK`。

当用户想要一个现成主题时（「用漫画主题」「装个 manga 主题」）：运行 `am theme add <name> --use`。名称来自 https://answer-me-with-html.com/themes/ 的目录（本文写作时有 `comic`、`manga`、`pop`）；如果名字不在其中，命令会列出可用的。它会下载、校验并保存主题、将其设为默认，此外不再询问用户任何事。如果它因同名文件已存在而停下，告诉用户那可能是他们自己的主题，只有他们同意时才加 `--force` 重跑。`am theme list` 显示已安装主题（`--remote` 同时显示目录），`am theme update` 更新它们，`am theme remove <name>` 删除一个。该命令只打印主题名和版本；需要 Answer me with HTML 0.5.3 或更高版本。

当参数以 `clean` 开头，或用户要求清理页面 / 缓存时：先运行 `am clean --dry-run`，告诉用户将删除多少项、多少空间。只有用户同意后才运行 `am clean`（加 `--all` 删除所有页面和视频，加 `--days N` 修改保留天数）。

当参数以 `update` 开头，或用户要求更新本 skill 时：按它的安装方式更新。用 `npx skills` 安装的：运行 `npx skills update answer-me-with-html -y`。作为 Claude Code 插件安装的：运行 `claude plugin update answer-me-with-html@answer-me-with-html`（或让用户在 `/plugin` → 已安装里点「立即更新」），然后让用户运行 `/reload-plugins`。用 git clone 安装的：在仓库目录运行 `git pull && npm install`。作为 DSH 插件安装的：运行 `dsh plugin --profile <name> up <package>`，profile 和包名从该副本自身路径里读出（`~/.dsh/profiles/<name>/node_modules/<package>/…`）；CLI 打印 `! Update hint` 或页面显示新版本按钮时，确切命令已经填好了——照打印的用。
