# AGENTS.md

## 工作原则

以瞎猜接口为耻，以认真查询为荣。
以模糊执行为耻，以寻求确认为荣。
以臆想业务为耻，以人类确认为荣。
以创造接口为耻，以复用现有为荣。
以跳过验证为耻，以主动测试为荣。
以破坏架构为耻，以遵循规范为荣。
以假装理解为耻，以诚实无知为荣。
以盲目修改为耻，以谨慎重构为荣。
以浪费时间为耻，以节省 token 为荣。

所有项目默认按 Windows 中文路径安全规则执行。

## GitHub Project 上下文

本项目对应 GitHub Project:
https://github.com/users/CeHePe/projects/1

新线程或新 agent 进入本仓库后，若任务涉及计划、issue、发布、主页完善、工作流或项目进度，必须先读取：

- GitHub Project #1: `gh project item-list 1 --owner CeHePe`
- Repo issues: `gh issue list --repo CeHePe/CeHePe.github.io --limit 100 --state all`

读取失败时，不要假装知道 Project 当前状态；应说明权限或网络问题，并基于本地仓库和可读取的 GitHub issue 信息谨慎推进。

## 本项目协作规则

### Git 与 PR

- 默认不要直接推 `main`。除非用户明确要求“推到远端”“上线”“发版”，否则先建 issue、推 feature branch、开 draft PR。
- 大改动必须拆小：列表页行为、详情页模板、内容文案、媒体优化、发布检查应分开追踪。
- 分支命名使用 `codex/` 前缀。
- PR review 完成前保持 draft；确认后再 ready/merge。
- 合并后及时清理本地和远端 feature branch。
- 推送或合并前先检查：
  - `git status --short --branch`
  - `git log --oneline --decorate -5`

### Issues 与 GitHub Project

- Issue 承载任务、内容审核、媒体审计和发布检查；PR 承载代码差异；GitHub Project 只用于看整体状态。
- 需要逐项确认的 issue 使用 task checklist，例如内容审核、媒体性能检查、发布检查。
- 涉及 GitHub Project 时优先使用 `gh project` 读取当前状态；权限不足时先处理 `project` scope，不要凭记忆更新。
- 本项目已知关键 issues:
  - #2: 推断文案审核
  - #3: 媒体资产与性能审计
  - #5: GitHub Pages 发布检查

### 内容与模板

- 未完成详情页不要从列表页直接暴露为可点击入口；可以保留卡片，但要加 `即将更新 / Coming Soon` 覆盖层。
- 中英双语按上下段落排列：中文段落在前，英文段落紧随其后。不要做左右双栏中英并排。
- 详情页统一结构：标题区、Overview、Process、Media、Details、Links。
- 标题区统一为：中文标题、英文副标题、工具/上下文、中文简介、英文简介。
- 新增或重写详情页从 `templates/detail-page-template.html` 开始。
- 公共样式集中在 `styles.css`，不要在每个页面临时写局部样式。
- 基于文件名或素材推断的文案必须标记待作者 review，尤其是 `cats`、`classroom`、`ue5`、`wand`、`budget`、`credit`。

### 发布与验证

- 发布前至少检查：
  - `/projects/`
  - `/projects/comfy/`
  - `/projects/touchdesigner/`
  - `/research/`
- GitHub Pages 上线后必须验证线上 URL，不只看本地预览。
- 发布前需要确认大图、视频、PDF、源文件是否适合继续放在公开 GitHub Pages 仓库中。
- 媒体优化和公开资产策略应放在独立 issue 中处理，不要混入模板或文案 PR。

### 工具与网络

- Windows 上 HTTPS + GitHub CLI 是本项目默认推荐认证方式。
- 若 GitHub Project 权限不足，执行 `gh auth refresh --hostname github.com --scopes project`。
- 如果 GitHub 网络不稳定，先检查代理。本机常见代理端口为 `127.0.0.1:1080`，可临时设置：
  - `$env:HTTP_PROXY="http://127.0.0.1:1080"`
  - `$env:HTTPS_PROXY="http://127.0.0.1:1080"`
- 如果命令失败，先查 `gh auth status`、token scopes、proxy 和远端状态，不要反复盲试。
