# 讲解视频（am video，3Blue1Brown 风格）

SKILL.md 第 7 节把你送来时读本文件。`am` 指 SKILL.md 第 2 节里完整的 `node ".../scripts/am.mjs"` 命令；路径要写全，因为本文件里 `${CLAUDE_SKILL_DIR}` 不会被替换。

视频草稿的格式与页面草稿相同，只多一条规则：以 `>` 开头的行是旁白，一行一个节拍。

````bash
am video - --no-open <<'AM_EOF'
---
title: The TCP three-way handshake
subtitle: Why three
---
> Opening narration (optional).

## Both ends are waiting
```sequence
Client -> Server: SYN
Server -> Client: SYN-ACK
Client -> Server: ACK
```
> First the client sends SYN to ask for a connection.
> [Server] answers with SYN-ACK.
> The client replies with ACK, and the connection is open.
AM_EOF
````

- 一个 `## ` 就是一个场景。每个场景放一个组件（或一个表格、一个列表）作为画面，下面写 2–5 行旁白。
- 第 N 行旁白播放时，画面显示第 N 步。flow / er / sequence / tree 里每条源行就是一步；timeline、limits、表格行和列表项按条目步进。所以组件的行序就是讲解的顺序。当旁白行数多于步数时，多出的行在前面作为开场，不展示新内容。
- 旁白里写 `[name]`：镜头推近到组件里同名的节点或参与方并高亮它。名称必须与组件里的写法一致。
- 相邻场景里同名的节点会平滑移动到新位置。要让观众盯住同一个对象，就在下一个场景里复用同一个名字。
- 每个视频 3–6 个场景，每行旁白一两句话。
- 旁白是要读出来的，所以按口语写，像面对面给人讲解：「你看」「那问题来了」「我们换个角度看」这类转场没问题，角色的「台词」放引号里。不要写成说明书腔（「客户端发送 SYN 报文以请求建立连接」）。句长仍受 STE 检查约束。
- 外观默认跟随设置里的主题（通常是蓝图绘图风格）。用户想要「3b1b 那种暗色风格」时，在 frontmatter 写 `theme: 3b1b`。
- 旁白音色：默认 `--voice auto`：设了 `ELEVENLABS_API_KEY` 用 ElevenLabs，否则用系统 TTS（macOS say），两者都没有时只出字幕。用户说「不要声音」时加 `--voice off`。用户跑本地 OpenAI 兼容语音服务并设了 `AM_TTS_URL` 时，用 `--voice local`。
- 产物是 `~/.answer-me-with-html/videos/` 下的单文件播放器页面（音频已内嵌）。播放器在控件上方有一条章节条（点胶囊跳进该场景）、一个倍速按钮（0.5× 到 2×）和一个导出按钮（⤓），导出在浏览器里编码同一个视频并下载，进度显示在按钮上。用户想要页面旁边的视频文件时，加 `--mp4` 得到 MP4（需要 ffmpeg，耗时约为视频时长的 1.3 倍）。没有 ffmpeg 就加 `--webm`：页面自行编码 WebM（VP9 + Opus）；耗时取决于页面动了多少（实测：11 秒的草稿 28 秒，2 分 27 秒的讲解 13.5 分钟）。两者都需要 Chrome 和 Node.js 22+。导出按钮需要安全上下文（本地文件或 `localhost`）：普通 HTTP 提供的页面用不了 WebCodecs。播放器页面为此增大约 19 KB。
- 完整语法：`am help video`。在终端里，回复一句话加上播放器页面链接（以及 MP4 链接），写法同 SKILL.md 第 2 节第 5 步。
