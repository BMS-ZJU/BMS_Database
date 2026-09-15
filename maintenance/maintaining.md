# 网站维护与交接

本指南面向接手 BMS Database 的维护者，说明怎样从仓库恢复工作环境、定位改动、发布和处理故障。课程内容与排版细则分别保存在对应指南中，当前任务、账户配置和私有材料另行交接。

## 接手时先跑通一处修改

从 [README](../README.md#本地预览与开发) 获取仓库并创建 Python 3.12 环境，安装 [requirements.txt](../requirements.txt) 中的固定依赖。生产构建使用同一 Python 版本与依赖文件，不需要 Node.js，也不需要模型 API 密钥。

以下命令在仓库根目录运行。Windows 使用虚拟环境中的解释器；macOS / Linux 可将 `python` 替换为 `.venv/bin/python`。

```powershell
.\.venv\Scripts\Activate.ps1
python -m mkdocs serve
```

打开终端给出的本地地址，先熟悉一门课程的主页、资料目录和资料正文，再做一处范围明确的修改。预览结束按 Ctrl+C。PowerShell 不允许激活脚本时，直接使用 `.\.venv\Scripts\python.exe -m mkdocs serve` 即可。

工作开始前运行 `git status --short`，确认所在分支和目标文件的已有差异。若正在使用的工作区混有其他任务，可以从最新主线另建 worktree；不把整份工作区清空或恢复为主线。

```sh
git fetch origin
git worktree add -b update/site-maintenance ../bms-site-maintenance origin/main
```

新 worktree 与原仓库共用 Git 历史，修改与虚拟环境各自独立。已有目标页草稿时，先记录其实际基线和从属关系，再决定采用哪份内容。具体编辑流程见 [贡献指南](../CONTRIBUTING.md)。

## 在哪里改

| 内容或行为 | 维护入口 |
| --- | --- |
| 正式网页、图片与下载文件 | [docs/](../docs/)，课程统一放在 [courses/](../docs/courses/)，课程专用图片与下载文件随课程保存 |
| 课程与校历结构化数据 | [data/courses.yml](../data/courses.yml)、[data/academic-calendars.json](../data/academic-calendars.json) |
| 全站共用图片、字体、样式与脚本 | [docs/assets/](../docs/assets/)，按 `brand/`、`fonts/`、`styles/` 和 `scripts/` 分类 |
| 导航、站点 URL、发布排除规则、脚本与样式加载顺序 | [mkdocs.yml](../mkdocs.yml) |
| 课程主页编辑 | [maintenance/course-homepages.md](course-homepages.md) |
| 试卷、小测、合集、来源与打印边界 | [maintenance/recall-papers.md](recall-papers.md) |
| 学年学期、校历日期与周次 | [maintenance/semester-reference.md](semester-reference.md)、[data/academic-calendars.json](../data/academic-calendars.json)、[scripts/academic_week.py](../scripts/academic_week.py) |
| 阅读样式、主题和字体 | [maintenance/reading-experience.md](reading-experience.md)、[docs/assets/styles/](../docs/assets/styles/)、[overrides/](../overrides/) |
| 页面标题与资料独立身份 | [hooks/page_identity.py](../hooks/page_identity.py) |
| 资料使用提示、原文与使用范围链接 | [hooks/resource_usage.py](../hooks/resource_usage.py) |
| 页面与公开资源迁移 | [data/path-migrations.json](../data/path-migrations.json)、[hooks/path_migrations.py](../hooks/path_migrations.py) |
| 合集旧网址及原页评论 | [hooks/resource_aliases.py](../hooks/resource_aliases.py)，配置写在合集页面的 `resource_aliases` 中 |
| 阅读页打印入口、独立导出与范围选择 | [resource-export.js](../docs/assets/scripts/resource-export.js)、[resource-export-view.js](../docs/assets/scripts/resource-export-view.js)、[resource-export.html](../docs/resource-export.html)、[resource-export.css](../docs/assets/styles/resource-export.css) |
| 公开投稿表单、站内页面选择器 | [.github/ISSUE_TEMPLATE/](../.github/ISSUE_TEMPLATE/)、[hooks/contribution_links.py](../hooks/contribution_links.py)、[contribution-picker.js](../docs/assets/scripts/contribution-picker.js) |
| 投稿处理、模型配置、限额与审阅 | [maintenance/contribution-intake.md](contribution-intake.md)、[scripts/contributions/](../scripts/contributions/) |
| 页面评论 | [overrides/partials/comments.html](../overrides/partials/comments.html)，使用 Giscus 连接本仓库 Discussions 的 `General` 分类 |
| 网站构建与发布 | [.github/workflows/deploy.yml](../.github/workflows/deploy.yml) |

`main` 保存可发布的源码，`gh-pages` 是由部署生成的站点。修改应回到源码，不直接修补生成的 HTML。`contribute/catalog.json` 也由构建生成，无需手工保存到 `docs/`。课程映射与页面列表在构建时更新；`python scripts/contributions/catalog.py --write` 同步网页预填表单的课程字段，并生成对应的仓库直填表单。网页入口保留课程文本预填，仓库直填入口提供课程下拉选项；直填表单由同一份源表单生成，不单独编辑。

公开仓库及 `docs/` 都不是私有材料存储。未进入导航的文件仍可能发布；`not_in_nav` 只豁免导航检查。草稿和内部文件按 `draft_docs`、`exclude_docs` 或迁出 `docs/` 处理，不能把 `.gitignore` 当作发布权限。

## 日常内容维护

先确认课程、适用学年与材料来源，再编辑页面。已发布题文和个人经验不能仅凭更新的投稿覆盖；有冲突时保留两边依据，待核对后再采用。课程主页没有可靠内容的栏目可省略；回忆卷缺题、缺图和存疑之处按原记录保留。

每份采用材料应有一条可追溯记录，至少包含目标页面、课程与时间范围、原作者和提供者、原始文件或出处、允许的用途、公开署名以及未确认项。公开 Issue 或 PR 可以记录能够公开的依据；私人联系方式、授权聊天和受限原件放在约定的非公开档案中。页面源码和 HTML 注释也会公开，不能存放敏感证据。仅有“页面内容相符”时，不将其写成已经确认的原始录入来源。

接手时应取得现有来源登记及其引用的原件，核对路径还能找到材料。新接手人的存储位置可以不同，但登记与原件之间的相对关系应保留。未获原有授权的内容先保留为待核对线索；网站收录、全文或附件转载、外部模型处理及 Ginkgo 使用分别确认，不能互相替代。

改动涉及使用方式时，同时查阅 [使用说明](../docs/guide/index.md)、[贡献与纠错](../docs/contribute/index.md) 及相关维护指南，只更新受影响的说明。旧页面若仍可访问，应保留有效入口并指向当前说明，避免继续承诺已经停用的人工服务。长期规则更新现有条目，当前工作状态通过对应 Issue、PR 或私有交接记录保存，不连续追加多份现行规则。

首页的[近期更新](../docs/index.md)只保留最近 3–5 条影响读者使用的变化，如新增资料、重要更正和功能变化。日期按实际上线时间记录，尚未发布的候选不列入；调整排版或技术实现不能写成“内容已复核”。发布时更新或替换已有条目，旧记录通过 Git 历史追溯，不把首页变成提交日志。

### 署名变更

按每个人参与的具体材料，分别核对署名名称、贡献角色、正文或源码中的显示位置及允许用途。对一份材料的约定不自动推广到该作者的全部资料；采用本人确认的网名时，正文与源码均不附实名或身份对应。

集体回忆、整理与个人发布、上传可以同时存在，按已确认分工分别写明。某一角色改为集体署名或不署名时，不据此删除其他已确认角色。确认多个账号属于同一人后，可合并重复署名并保留各自的贡献；身份对应及确认依据只留在非公开记录中。补充提到共同整理者的姓名，只作为来源线索，不代替其署名方式的确认。

修改后核对相关材料、课程主页与来源注释，按实际影响检查可见署名及打印保留情况。仅更新署名时，题目、答案与原有课程内容保持一致；联系进度和待确认事项继续留在维护记录，未回复不视为同意。

### 重要更正与相关版本

题干条件、答案、考核比例、适用学年或使用范围发生重要更正时，先记录具体页面与位置、原有内容、更正依据和影响范围，再检查相关版本。相近题目或不同学年不能仅因内容相似一起修改。

1. **本站正文与入口。** 核对同一材料在原页、合集、课程主页和资料目录中的相关表述；更正属于哪个学年或班次，就保留在对应范围。由同一正文生成的旧网址无需另存一份题文，但要检查是否仍指向正确材料。
2. **答案与打印。** 题干或答案变化时同时检查已有随题答案、静态答案表和必要说明。自动生成的卷末答案及打印稿以源页面为准，不直接修改生成文件；按实际影响核对相应答案模式、选定材料与来源链接。外部已经保存的 PDF 不会随网页自动更新。
3. **Ginkgo 等关联版本。** 有对应练习或转载版本时，在维护记录中登记链接、需核对的更正和同步状态；按维护安排联系相应维护者，经核对后记录结果。本站更新不代表外站已经同步，练习版补充的选项或答案也不能反向认定为原题。
4. **告诉受影响的读者。** 对会影响理解、作答或使用的重要更正，在资料相应位置保留必要说明，并在首页近期更新中简短记录课程、材料、更正内容与影响；需要时提醒已保存旧稿的读者重新导出。通知日期按更正实际上线时间填写，标点和纯样式调整不发内容更正提示。

交接记录至少写明更正日期、依据、受影响页面或材料、已经检查的版本，以及仍待核对的关联版本。来源争议和未确认答案继续标明不确定性，不用“已同步”概括尚未核验的项目。

## 图片体积与压缩

新增、替换或集中检查图片时，先记录文件体积、像素尺寸、格式、透明度和实际引用页面。默认从不小于 **250 KiB** 的图片开始排查，优先处理超过 **1 MiB** 的文件；这是筛选起点，不是每张图片的硬性上限。体积已经合适的图片、SVG 和图标不为统一格式反复转码。

- **先做无损优化。** 原 PNG 可以重新编码，采用前逐张比较解码像素、尺寸、透明度和元数据，确认完全一致；体积没有实际收益时保留原文件。文件哈希用于核对备份和构建产物，不能用压缩前后文件哈希不同来判断像素是否改变。
- **为大图制作正文版。** 无损优化后仍偏大的图片可另存同名 WebP，质量参数从 `92` 起试，默认保留原分辨率、比例和透明度。对比原图中的文字、曲线、细线、凝胶条带和标本细节后再采用；不为达到统一体积而裁切或降低关键细节的可辨认程度。
- **保留原图入口。** 正文使用压缩版，点击后仍打开原 PNG 或原格式文件，已有原图网址继续有效。原图只做经核对的无损优化，不用有损正文版覆盖。图片与原图链接的写法见[回忆卷指南的图片部分](recall-papers.md#3-图片)。
- **按实际引用更新。** 解析相对路径后再替换图片地址，避免不同课程的同名文件被误改；保留替代文本、宽度和样式。核对实际发布的单页与合集。已冻结的小测源码及 `preserved_source_sha256` 按[旧网址规则](#标题打印与旧网址)保留，不能为图片优化改哈希绕过检查。
- **验证实际加载与阅读。** 更换格式或图片引用后运行严格构建，核对正文图和原图均可访问，并检查正文是否仍通过预加载额外下载大原图。逐图比较压缩前后，选择代表页面检查电脑、手机、明暗主题和新旧阅读样式；题图同时核对独立导出。只检查打印媒体预览时如实记录，涉及打印尺寸或分页变化时按[验证要求](#按改动选择验证)实际输出 PDF。
- **分开记录两类体积。** 记录原文件、无损优化后的原图、正文版各自的字节数，以及正文加载体积和包含原图在内的全部图片资产体积。压缩参数、逐文件结果和验证证据保存在任务记录中，不把一次压缩比例写成后续必须达到的标准。

## 标题、打印与旧网址

导航名称可以简短，页面在标签页、收藏夹和独立分享中应能辨认课程及材料。课程与资料身份由标题构建逻辑结合页面内容和课程映射处理；修改标题后，应分别检查浏览器标题、正文 H1 和导航，不能只看侧栏。页面内容范围扩大或文章名称调整时，同步相关首页、分组页和正文入口名称；仅改显示名称时保留既有文件路径、网址和章节锚点。

考试与小测的独立打印页从正式网页获取题文，不另存一套待人工更新的 PDF。导出要保留课程、学年、材料性质、原有公开署名与来源说明，并能返回原文；小测合集还要识别所选材料和对应锚点。适用学年或学期未知时保留不确定性，不能为了标题完整补造信息。打印排版与屏幕阅读分别检查，具体范围和答案方式见 [回忆卷指南](recall-papers.md)。

移动页面前先检索引用、现有锚点和评论关联，并在 [data/path-migrations.json](../data/path-migrations.json) 登记旧路径与当前路径。`pages` 和 `assets` 使用 `docs/` 下的相对路径，分别生成旧页面跳转和旧资源副本；`source_files` 使用仓库相对路径，记录维护文档及数据文件的位置变化，不生成网站入口。页面迁移目标可带章节锚点，旧链接已有查询参数或锚点时继续保留；没有旧锚点时使用登记的目标位置。兼容页不加入导航或搜索，正文只维护当前页面。

Giscus 原来按网址路径关联讨论。单页改名后，迁移逻辑让当前页沿用旧评论路径；多个旧页合并、带章节目标或已有合集讨论时，仍需单独核对讨论归属。小测并入合集继续按 `resource_aliases` 保留旧阅读位置、导出分组和原页评论，再由路径迁移衔接旧目录。已登记 `preserved_source_sha256` 的原文件变化会使构建停止，先核对原文与合集，不能直接改哈希绕过差异。

核对兼容入口时，至少从旧页面网址、带锚点的分享链接、旧题图或下载地址和独立导出入口各走通一处，并确认当前页面的原讨论仍可找到。不要仅凭新页面能够打开就移除迁移记录。

## 按改动选择验证

纯文字反馈检查相关事实、链接和 Git 差异即可。新增页面结构、导航、共享脚本或样式，以及准备发布时，运行严格构建。使用专门的外部输出目录，避免覆盖其他任务的预览；以下目录只用于本次构建：

```sh
python -m mkdocs build --strict --site-dir ../bms-maintenance-preview
git diff --check
```

严格构建通过后，从本地服务打开生成站点，核对本次新增或改动的入口。涉及共享阅读交互时选择桌面、手机和明暗主题的代表样本；打印变化还需实际输出 A4 PDF，核对标题、题图、公式、答案归属、原文链接及分页。屏幕截图或 `@media print` 预览不能替代实际 PDF。

脚本变化按相关测试运行；以下测试使用本地模拟，不发起真实模型请求：

```sh
python -m unittest discover -s tests -p "test_academic_week.py"
python -m unittest discover -s tests -p "test_contribution*.py"
```

`Deploy documentation` 的 PR 检查目前只执行严格构建，不能代替投稿脚本测试和浏览器检查。新改动、失败或未覆盖的实际影响才需要扩大验证。提交前核对 `git diff --stat` 和目标路径差异，仅用 `git add -- <明确路径>` 暂存已审内容。

## 发布与回退

多项任务合并发布时，记录各候选的来源工作树、基线提交和实际文件版本，针对共享文件合并各自差异，不整份覆盖较新的主线。原任务在汇总后继续更新时，重新核对变化、累计范围和相关验证；旧候选的构建或截图不能作为更新后版本的验收依据。

正常发布入口是合并到 `main` 的 PR。`Deploy documentation` 在 PR 中仅构建；`main` 收到推送后先严格构建，通过后由 `deploy` job 执行 `python -m mkdocs gh-deploy --force`，使用 GitHub 自动提供的 token 写入 `gh-pages`。该工作流不需要维护者新增 PAT。仓库 Settings → Pages 应与这条发布方式对应，来源为 `gh-pages` 分支根目录；接手或迁移时由管理员核对实际设置。

一次发布应确认这三层结果：

1. PR 已合并，`main` 中的实际文件与批准差异一致；
2. 对应提交的 `Deploy documentation` 和后续 Pages 构建发布成功；
3. [正式网站](https://bms-zju.github.io/BMS_Database/) 的受影响页面、资源和旧入口已经显示批准内容。网页返回 HTTP 200 只能证明可访问，还要核对正文与关键资源。

需要回退时，先确定引入问题的提交和受影响范围。从最新 `origin/main` 创建修复分支，恢复批准的旧内容并走同一 PR、构建和部署流程。单个普通提交可以用 `git revert --no-commit <提交号>` 准备反向差异，再审阅、验证并提交；合并提交或有后续修改时，先核对父提交及依赖，不机械套用该命令。不对共享主线强推，不把其他人的后续工作一起撤销。`gh-deploy --force` 只用于既有生成分支部署，不是源码回退方式。

发布记录至少保留合并提交、部署运行链接、核对的正式页面与实际验证边界，供下次定位。投稿的 `contribution-ledger` 是独立持久账本，不随网站回退清空、回滚或重建。

## 账户与私有材料怎样交接

能克隆仓库不等于能接管运行环境。交接双方应在各服务实际验证新维护者的访问与职责，用非公开记录保存管理员、恢复方式和未完成事项，不在仓库中填写密码或密钥。

| 交接对象 | 需要确认的内容 |
| --- | --- |
| GitHub 组织与仓库 | 新维护者能处理 PR、Issues 与 Discussions；指定管理员能调整 Pages、Actions、Environment 和 ruleset，至少有明确的恢复联系人 |
| Pages 与评论 | 发布来源、最近成功部署、Giscus App 安装和 Discussions 分类可用；更换仓库时同步 `mkdocs.yml`、评论中的仓库/分类 ID，并处理旧网址与旧讨论 |
| 来源档案与未公开材料 | 来源登记、原件及备份可访问；署名、撤回、匿名和每种使用授权能对应到材料；在非公开渠道移交联系人与待确认项 |
| 非公开联系与撤回请求 | 核对[非公开联系入口](../docs/contribute/index.md#contact)仍可使用，新维护者有收件与回复权限；交接尚未处理的署名、撤回和隐私请求。变更联系方式时更新该入口，其他说明继续链接到它 |
| 正在处理的内容 | 区分已发布、已合并但待部署核验、待审草稿及未处理投稿；记录分支或 PR、基准提交、唯一候选和下一步，不把旧待办视为仍有授权 |
| 已启用的模型服务 | 服务账户负责人、费用承担与限制、`contribution-model` Environment 的 Secret 管理权、Variables、分支 ruleset，以及实际启用状态 |
| 投稿账本 | `contribution-ledger` 分支、首次锚点 `CONTRIBUTION_LEDGER_ANCHOR`、认证密钥 `CONTRIBUTION_LEDGER_KEY` 的安全保管，以及 unknown 或未结预留 |

公开投稿会立即进入 GitHub Issue；网页选择器不会替投稿者发帖。收件与人工编辑可独立运行。仓库默认把 `scripts/contributions/repository.json` 的 `real_calls_enabled` 设为 `false`，`policy.json` 中累计额度为 `0`；实际云端配置与启用条件按 [投稿处理维护指南](contribution-intake.md) 核对，不因代码存在就视为模型已启用或完整链路已验证。

模型处理只有维护者手动发起的快照与批准流程，候选仍须人工采用；不会自动回复 Issue、建 PR 或发布。交接时优先保持处理开关关闭，先核账。账本密钥不能按普通服务密钥直接替换：改动后已有账本无法认证，需保留原密钥与锚点并按投稿指南处理。Actions 快照和候选产物只保留七天，不能作为长期来源档案或私有备份。

## 常见故障从哪里查

| 现象 | 第一处检查与处理 |
| --- | --- |
| 严格构建失败 | 看首条实际警告或异常的文件路径，检查 `mkdocs.yml`、内部链接和对应 hook。区分本次引入的问题与原有问题，避免通过关闭严格检查掩盖错误 |
| 提示“投稿课程字段已过期”或“仓库投稿表单已过期” | 核对 `scripts/contributions/catalog.py` 中的字段定义，运行 `python scripts/contributions/catalog.py --write` 并审阅四份表单差异 |
| PR 构建成功但网页未更新 | 确认已合并至 `main`，再看 `deploy` job、Pages 设置与后续 Pages 运行；对比正式正文和资源，不只刷新首页 |
| 页面出现 404 或旧链接跳错位置 | 核对路径大小写、`site_url` 的项目子路径、导航目标、`data/path-migrations.json` 与 `resource_aliases` 锚点；确认兼容 HTML 已生成 |
| 标题仍显示“课程主页”或无法区分材料 | 核对目标 Markdown、课程映射、标题 hook 的生效顺序和构建后的 `<title>`，再检查导出所选范围 |
| 导出失败、乱码或题图缺失 | 从资料目录进入独立导出页；检查浏览器控制台和网络请求、原文/图片/字体加载及范围锚点。使用 HTTP 本地服务预览，应用内浏览器问题先换系统浏览器 |
| 公式或评论单独不显示 | 公式依赖配置中的 KaTeX 资源，评论依赖 Giscus 与 GitHub Discussions；分别检查网络请求、评论 App/分类权限、路径关联与主题，不把服务问题当作题文丢失 |
| 投稿模型步骤停止 | 根据失败 job 和 `receipt.json` 定位，按投稿指南核对开关、权限、快照、额度与账本。超时或未知用量不点击 Re-run jobs，也不删除账本来“恢复” |

遇到隐私或凭据泄露，先停止相关投稿处理并限制继续传播，通过适当的非公开渠道联系有权限的人处理公开内容与相关记录。删除源码或关闭 Issue 不代表历史、附件和已发布副本已经消失。具体处置范围和结果应单独记录，不把敏感证据贴回公开反馈。
