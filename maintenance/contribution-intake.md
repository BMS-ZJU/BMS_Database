# 投稿处理维护指南

第一版使用 GitHub Issue 表单接收公开文字、附件和线索。投稿者不需要修改仓库。资料表单填写新材料或经验, 纠错表单分别填写“问题位置与现状”“建议修改”; 后续共用受限处理流程。熟悉项目的人可按[直接修改教程](../docs/contribute/editing.md)提交 PR, 多页相关修改不必拆成多个 PR。

当前功能状态: 投稿入口、人工审批、持久账本、三家官方模型服务适配与审阅产物代码已具备, **真实调用默认关闭, 累计额度为零**。完整 GitHub 审批、账本和模型链路尚未完成云端验收。收件和人工修改无需模型配置。

## 课程与页面选择

站内下拉框支持输入关键词筛选，按课程名称、代码、页面标题或学年匹配。搜索文字必须经点击或回车选定为现有选项才可继续，未匹配文字不会进入目标URL；修改课程搜索会清空旧页面。保留键盘、中文输入法和触摸操作。课程筛选在站内完成, GitHub 使用文本字段接收已选课程。

网站的[选择投稿页面](../docs/contribute/submit.md)由课程映射和本次构建实际发布的页面生成下拉列表。选择课程后只显示该课程页面, 切换课程清空旧页, 可以添加多条页面选择并逐页打开 GitHub 填写。每次只打开一张表单, 不保存投稿正文、不自动发帖, 不把打开填写页记成已投稿。

GitHub 的 New issue 中, 普通资料/纠错表单使用课程下拉框。需要输入关键词匹配或逐页投稿时, 可选“搜索课程与页面后投稿”进入网站。网站继续跳转到带“网页预填”标记的文本字段表单, 通过 course 参数带入名称与代码, 不再要求重复选择课程。原有网站链接保持有效; 网页预填表单直接打开时仍可按页面地址匹配。

material.yml、correction.yml 是共用字段的维护来源; python scripts/contributions/catalog.py --write 根据它们生成 material-direct.yml、correction-direct.yml 仓库直填版本, 只改变入口名称、说明和课程控件。授权字段、字段标识和处理逻辑共用。修改字段或课程映射后运行同步, 将四份表单一起提交; 构建检查派生表单完整一致性, 不手工维护第二套授权说明。课程映射和页面增删在构建时更新 contribute/catalog.json。课程代码用于同名消歧, 未发布草稿和退休别名不进入列表。

处理脚本在任何模型调用或产物写入前, 核对本站页面 URL 和维护者选择的目标文件。默认匹配只接受与目标完全对应的本站页面地址, 不从标题推测课程, 不因维护者填写了目标就补全缺失地址; 手动选择课程时另核对课程名称与代码。原始选择和页面地址保留在快照中, 修改任一项需重新批准。地址缺失或任一不匹配均停止并留给人工处理; 公共页面和未知课程可投稿, 本版自动候选仍限已登记的现有课程页。Issue 提交后正文可编辑, 文本预填不能代替处理端验证。

新表单必须先进入仓库默认分支才能在 GitHub 生效。本地预览只能验证站内交互和链接参数; 发布后还需核对真实登录状态下的表单、预填值和提交结果。

## 处理范围

- 只接受可以立即公开的投稿。公开 Issue、其附件和本仓库的 Actions 产物都不能作为私密收件箱。需要非公开核对时, 先只收线索, 按[来源与使用范围](../docs/contribute/sources-and-permissions.md)确认适当渠道。
- 投稿者可以不授权整理, 或不同意外部模型处理; 这种投稿仍正常接收, 进入人工核对。
- 每次由维护者选定一页现有课程 Markdown。模型只生成最多三处文字候选, 不创建 PR、不提交、不合并、不发布。
- 第一版不下载附件或访问投稿链接, 不做 OCR 或复杂文档转写。上传文件可以进入收件队列, 但文件内的图片、表格、公式与事实仍待人工提取核对。只有标题或附件链接时, 不能声称已读完整材料。
- 可根据投稿文字补充资料介绍和获准展示的入口。没有对应课程页、需要新建整份回忆卷、较大重组或含 HTML、公式等结构的修改, 按现有贡献指南人工处理。
- 投稿里发现事实冲突时保留原页, 分开列出依据与疑问。新学年材料不自动覆盖旧学年版本, 不推算未知比例、不补题或答案。
- 本站文字、原附件、外部模型整理和 Ginkgo 使用分别登记。系统不向 Ginkgo 传送或生成修改。

## 查看并批准快照

同学提交或编辑 Issue、发表评论、提交 PR 和访问网站都不会调用模型。本流程只接受默认分支上的 workflow_dispatch, 并通过 GitHub API 核对运行事件、仓库、提交、首次运行和真实操作者的 maintain / admin 权限。投稿者的服务同意是材料授权, 维护者手动批准才是执行和支出授权; 正文、标签和“管理员已批准”等文字不能授予权限。

1. 先确认 Issue 的文字与附件入口允许公开。权限不明、含隐私或疑似密钥时转人工处理, 不生成公开快照。
2. 在 Actions 的“整理公开投稿”中选择 operation = snapshot, 填写 issue_number 和 target_page。目标仍是一页已登记的课程 Markdown, 如 docs/courses/neuroscience/index.md。此操作不提供模型密钥, 不调用模型。
3. 下载该次运行的 snapshot-运行编号, 阅读 review.md。它列出完整投稿、附件入口清单、来源行、完整目标页、基准提交、拟用服务与模型、规则与额度配置。附件清单只标识正文中的入口; 没有下载文件, 也不代表核验过附件内容。
4. 确认后另开一次手动运行, 选择 process, 填入该快照的 snapshot_run_id 和完整 snapshot_sha256。填写这两项表示维护者实际审阅并批准这一快照的一次调用。不能只填 Issue 编号。
5. 程序在额度预留前和调用前分别核验快照来源、哈希、真实维护权限、当前 Issue、目标页、默认分支及配置。正文、标题、更新时间、附件入口、目标或可信代码发生变化时停止。默认分支其他提交也会使旧快照失效, 第一版采用此保守规则。
6. 同一快照只能获得一次处理授权。重复点击 process、重新运行旧任务或并发提交不能再次付费。若确需重做, 必须重新生成并审阅快照, 再给出新批准; 不使用 Re-run jobs 续接付费任务。

快照产物保留七天; 过期或删除后需要重新生成, 不从 Issue 最新版静默补齐。冻结依据是完整正文与目标版本; 不跟随附件 URL 验证远端二进制内容变化。执行过程中始终使用通过核验的冻结输入。

## 配置服务、Secrets 和额度

在默认分支的 scripts/contributions/policy.json 中配置限额, 经正常维护流程审阅。累计额度默认都是 0, 未明确配置不能调用。可信仓库身份与第二道开关保存在 scripts/contributions/repository.json: repository 必须是 BMS-ZJU/BMS_Database, real_calls_enabled 默认 false。该文件和服务、模型、页面版本一起绑定快照; 配置缺失、仓库不一致或批准后发生变化均停止。实际请求前再次读取默认分支上的配置, 不把投稿文字当作配置。首次启用需经审阅把 real_calls_enabled 改为 true, 仅设置下方 Variable 还不能调用。

服务与运行开关使用 Actions Variables:

这些 Variable 放在 Settings → Secrets and variables → Actions → Variables 的仓库层级, 不另外建立同名 Environment Variable。

| Variable 名称 | 何时必填 | 用途与初始填写值 |
| --- | --- | --- |
| CONTRIBUTION_AI_ENABLED | 真实处理时必须为 true | 初始填 false; 未设置也关闭。snapshot 和 initialize 不要求开启 |
| CONTRIBUTION_MODEL_SERVICE | snapshot 和 process 必填 | 选择 DeepSeek、OpenAI 或 Gemini, 大小写一致; 必须与投稿者同意的服务匹配 |
| CONTRIBUTION_MODEL_NAME | 可选 | 下表的 API 模型 ID; 留空使用所选服务默认值 |
| CONTRIBUTION_LEDGER_ANCHOR | process 和 reconcile 前必填 | 只填首次 initialize 输出的40位提交 SHA; snapshot 和首次 initialize 不需要 |

| 服务 | API 模型 ID | Actions Secret |
| --- | --- | --- |
| DeepSeek | deepseek-flash (默认, 核对时官方版本为 DeepSeek-V4.1-Flash; 实际响应可能只返回模型别名) | CONTRIBUTION_DEEPSEEK_API_KEY |
| OpenAI | gpt-6-astra (默认) | CONTRIBUTION_OPENAI_API_KEY |
| Gemini | gemini-flash-latest (默认) 或 gemini-pro-latest | CONTRIBUTION_GEMINI_API_KEY |

上表三把服务 Secret 只需填写实际使用的那一家。CONTRIBUTION_LEDGER_KEY 是另一把必填 Secret, initialize、process、reconcile 都需要; 纯 snapshot 不需要任何 Secret。用途和格式见下文。github.token 由 GitHub 自动提供, 无需填写 GH_TOKEN 或另建 PAT。代码没有读取金额预算 Variable 或自定义 Base URL, 不配置这类占位项。

先在仓库 Settings → Environments 新建 contribution-model, Deployment branches and tags 选择 Selected branches and tags, 只添加当前默认分支的精确 branch 规则, 不添加通配符或 tag。把上述密钥放在这个 Environment 的 Secrets 中, 不放在仓库级或组织级同名 Secrets; 若先前配置在其他层级, 移除那里的副本。模型 job 声明该 Environment, 程序在预留和调用前还会检查分支规则; 环境缺失、允许任意分支或规则读取失败都会阻止调用。[GitHub 环境与分支限制](https://docs.github.com/en/rest/deployments/environments)

只配置要用的服务密钥即可, 不把密钥发到聊天、Issue 或文件中。三个互斥的调用步骤分别只注入所选服务的一把密钥。没有该服务密钥时停止, 不使用其他服务密钥。切换服务时同步清空或修改模型名, 并重新生成和批准快照; 不沿用旧服务的材料授权。默认分支的工作流、脚本和规则必须通过维护者审阅进入。另设一个针对默认分支的 Active Branch ruleset, 开启 Restrict updates, 仅将可信 maintain/admin 加入该规则的 bypass; 普通 write 不应能直接修改可信代码。程序会核对生效的 update 规则, 缺失即停止。不要把这个 bypass 放到下文账本规则里。配置规则和 Environment 需管理员权限; maintain/admin 才能批准模型处理, 普通 write 身份不满足。代码入库不自动修改这些设置。

同一 Environment 还必须配置独立的 CONTRIBUTION_LEDGER_KEY, 用于认证账本, 不能复用模型密钥。它是本机安全生成的32字节随机数, 以64位小写十六进制保存; 可在自己的终端运行 `python -c "import secrets; print(secrets.token_hex(32))"`, 直接填入 Environment Secret, 不粘贴到聊天或投稿。仅账本读写步骤和调用前校验步骤注入它, 不进入模型输入、候选构建或产物。妥善保存, 不直接轮换或删除; 密钥缺失或更改会使已有账本无法认证并停止调用, 不因此建立空账本。

三家固定直连官方 API: DeepSeek 的 https://api.deepseek.com/chat/completions, OpenAI 的 https://api.openai.com/v1/responses, Google AI Studio 的 https://generativelanguage.googleapis.com/v1beta/models/{模型}:generateContent。Gemini 使用 x-goog-api-key 请求头, 其他两家使用 Bearer。投稿和模型不能指定接口地址、模型名或参数; 不使用 Vertex AI, 不跨服务回退。

| policy.json 字段 | 默认值与实际限制 |
| --- | --- |
| max_submission_chars | 10000, 投稿正文字符数 |
| max_page_chars | 30000, 指定页面字符数 |
| max_input_chars | 50000, 完整规则和序列化模型输入的总字符数 |
| max_output_tokens | 4096, 传给 API 的生成 token 上限, 可设128至6000 |
| max_calls_per_approval | 固定1, 第一版不允许增加或自动重试 |
| max_in_flight | 默认1, 可设1至3, 由共享账本限制未完成的预留 |
| cumulative_calls | 默认0, 所有投稿共用的累计调用预留次数 |
| cumulative_input_chars | 默认0, 所有投稿累计输入字符预留 |
| cumulative_output_tokens | 默认0, 所有投稿累计生成 token 预留 |

这是跨运行的硬性调用与资源配额, **不是供应商账单金额上限**。输入字符不等于输入 token; 本版不硬编码价格、不按未知 tokenizer 换算费用、不声称软提醒能限制金额。需要货币金额硬上限时, 必须另行确认提供方账户支持的硬限制并配置, 或保持付费开关关闭。接口返回的实际 token 用量会记录, 但不用于自动退回预留额度。

首次真实试运行建议只开放一次: cumulative_calls = 1、cumulative_input_chars = 50000、cumulative_output_tokens = 4096, 其余保留表中默认值, 尤其 max_in_flight = 1 和 max_calls_per_approval = 1。这些是 policy.json 字段, 不是 Actions Variable。提交代码不会开启真实调用或修改零额度。

首轮确认后需要扩大时, 可经审阅改为累计3次、150000输入字符、12288生成token; 是总量提高到3次, 不是再送3次。均不代表固定金额。降低额度后若低于已预留总量, 后续调用停止; 提高额度会使旧快照失效, 必须生成并批准新快照。

配置顺序: 先让本链路代码经正常审核进入默认分支 → 配置 Environment、账本 Secret 和 ruleset → 保持开关 false 运行 initialize 并保存首次锚点 → 填写服务和对应 Secret、审阅 policy.json → 最后才按明确授权同时启用 repository.json 的 real_calls_enabled 和 CONTRIBUTION_AI_ENABLED。默认分支尚无该工作流时, GitHub 不会显示它的 Run workflow 入口。

## 持久账本与故障处理

失败时下载 receipt-<处理运行编号> 中的 receipt.json。stage 区分请求、响应解析、候选校验与用量核验; failure.code 可为 AUTHENTICATION_FAILED、HTTP_ERROR、TIMEOUT_UNKNOWN、OUTPUT_LIMIT、INVALID_JSON、CANDIDATE_REJECTED、MODEL_RESPONSE_REJECTED 或 USAGE_UNCONFIRMED。回执保存可确认的模型版本与用量、有限结束状态以及计数, 不保存思考正文、供应商错误全文或被拒绝的完整回答。输出不完整、非法 JSON 或候选冲突都不会自动重试; 有效候选才进入 review 产物。failure.detail 和日志只显示可信程序中预先存在的错误文字。


先在 Settings → Rules → Rulesets 添加作用于 contribution-ledger 的 Branch ruleset, Enforcement 设为 Active, 开启 Restrict deletions 与 Block force pushes, 不设置任何 Bypass list。这两项不禁止正常快进写入, 不需要让 Actions 绕过规则。程序在初始化、预留和调用前核对这两个生效规则; 只配置旧式分支保护而没有可读取的 ruleset 不满足本版门槛。GitHub 的只读规则接口不公开绕过名单, 因此维护者启用前仍须在设置中亲自确认名单为空。[GitHub 生效规则接口](https://docs.github.com/en/rest/repos/rules#get-rules-for-a-branch)

随后有权限的维护者手动选择 initialize。它只创建独立的 contribution-ledger 分支, 分支里只有经过密钥认证的 ledger.json, 不包含网站和工作流。把首次运行摘要输出的锚点填入 CONTRIBUTION_LEDGER_ANCHOR。再次 initialize 不清空账本, 不替换原锚点, 也不能作为额度重置方法。正常处理路径不自动初始化或修复缺失账本。

账本用 HMAC-SHA256 认证完整记录、仓库和父提交。普通仓库写入者即使用快进提交清空计数、伪造结账或重放旧文件, 也不能获得有效认证; 删除和强推规则另外防止将整个引用退回旧的有效提交。不要手工清空记录或移动锚点绕过额度。具有仓库管理权限的人仍能改变配置和保护, 本流程不能对抗掌握管理权限的恶意管理员。账本丢失、认证失败、损坏、超过容量、锚点不符或读取失败时停止, 不当作空账本继续。

额度预留 job 通过 Git Database API 创建以已读账本提交为唯一父提交的新记录, 再以 force: false 更新固定分支引用。并发写入形成兄弟提交, GitHub 的原子快进检查最多接受一个, 失败者停止而不盲目覆盖或重试。记录按快照和处理运行去重, 在请求前全额占用额度; 不依赖 Actions cache 或会过期的产物保存累计计数。[GitHub 引用更新说明](https://docs.github.com/en/rest/git/refs#update-a-reference)

- 请求超时、网络错误或响应状态无法核对: 不重发请求; 记录 unknown, 后续调用停止。请求可能已到达供应商, 不能按“失败”自动退费或重试。
- 调用步骤未开始、任务取消或账本更新失败: 预留仍保留。后续检查发现运行已结束却没有结账时停止。
- 响应缺少可核对的生成用量或超出预留 token 上限: 不生成合格候选, 等待人工核账。
- 输出结构、证据、范围或安全校验失败: 不生成候选; 若已有有效用量仍登记本次消耗, 不触发自我修复或第二次请求。
- 账本并发冲突: 当前步骤停止。若发生在结账阶段, 保留未结记录, 不把它当作可重新调用的批准。

处理 unknown 或滞留预留时, 先在供应商控制台核对并确认相关工作流已经结束, 再手动选择 reconcile, 填写该记录的 approval_id。此操作将整个预留按已消耗结账, 保留未知实际用量, **不退回额度、不重置批准、不再次调用模型**。若无法确认, 保持阻断。需要重新处理的材料走新的快照和批准。

一键停止后续工作流: 在 Actions 的“整理公开投稿”菜单选择 Disable workflow。也可经维护流程把 repository.json 的 real_calls_enabled 改为 false; 程序在请求前重新读取此文件。也可把 CONTRIBUTION_AI_ENABLED 改为 false 禁止新运行的付费步骤。已经开始的运行应另行 Cancel; 已发出的请求不能撤回, 应按未知状态核账。紧急需要切断服务时停用对应供应商密钥, 不删除账本。

## 权限隔离与候选审阅

| 阶段 | 权限和输出 |
| --- | --- |
| 免费快照 | 仓库、Issue、Actions读取; 无模型密钥, 只生成快照与摘要 |
| 预留与结账 | 只有这些账本阶段持有 contents: write; 无模型密钥, 只更新固定账本分支 |
| 模型调用 | contents / issues / actions: read; 当前服务密钥和账本认证密钥, 不持有仓库写权限 |
| 候选构建 | contents: read, 无任何 Secret; 从内存替换这一页的读取结果并输出临时静态站点, 不改写源文件 |
| 提交和发布 | 本流程未实现自动提交或 PR, 由维护者审阅后走既有维护流程 |

工作流与代码检出固定为本次默认分支的 github.sha, 处理脚本和规则从这个可信版本读取。投稿、附件名、链接和已有页都是不可信数据, 不作为命令或配置执行。工作流不运行投稿者的分支、脚本或候选代码。输入通过环境变量或文件传入, 不拼接成 Shell。

模型没有终端、文件系统、网络浏览或 GitHub 工具。每次只生成最多三处限定替换, 不能选择路径或扩展范围。程序独立检查目标目录、符号链接、原文唯一匹配、完整候选的元数据、修改规模与真实渲染结果; 提示词不是权限边界。正常 Markdown 和安全的 Material 组件继续支持, 危险 HTML、执行属性、解码后的危险链接和包含/模板指令被拒绝。

候选审阅材料位于 candidate-运行编号; 构建成功后的完整包为 review-运行编号。下载后打开 review.html 或 review.md, 对照原文与建议、原始投稿行、疑点和冲突, 再查看 site/ 预览。必要时在解压目录启动静态服务。产物包含批准快照哈希、目标基准、服务、请求模型 ID、接口返回的模型版本和可用的 token 用量。Gemini latest 是动态别名, 不猜测没有返回的实际版本。

模型回答不会自动回复公开 Issue; 工作流不发评论、不创建 PR、不推送主分支、不合并或部署。无论模型是否“保证安全”, 维护者仍需核对语义、课程事实、材料使用范围、署名以及采用时页面是否已改变。原句定位只证明投稿包含该引文, 不等于附件页码或事实属实。

## 维护者从收件到采用

1. 在仓库 Issues 查看新投稿。自动化没有创建单独收件队列或自动评论, Issue 本身就是收件记录。核对公开许可、资料用途、课程/页面和模型服务同意; 未同意模型的直接人工处理。
2. 到 Actions → 整理公开投稿 → Run workflow, 选择 main, operation 选 snapshot。填 Issue 编号和目标文件路径; 其余输入留空。target_page 可从目标网页的编辑入口确认, 必须是现有课程 Markdown。维护者需要 maintain/admin 权限; 只有 write 权限也会被本程序拒绝。
3. 等待这次运行成功, 打开运行详情的 Summary。在 Artifacts 区下载 snapshot-运行编号 并解压, 打开 review.md, 核对完整投稿与目标原文。Summary 和 review.md 都列出快照运行编号和 SHA-256。[GitHub 手动运行](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow)、[下载产物](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts)
4. 再次 Run workflow, 仍选 main, operation 改为 process, 填 snapshot_run_id 和 snapshot_sha256。issue_number、target_page、approval_id 留空。提交这次运行就是对该快照的一次处理批准, 不需要在 Issue 写“已批准”或改标签。程序核验成功后会自动预留额度、调用一次、结账和构建; 正式工作流没有演示中的独立“生成”按钮。
5. 在 process 的运行详情查看各 job。reserve 失败表示未取得付费资格或预留; model 失败可能已产生费用, 按前文未知状态处理。preview 成功后, 在同一次运行的 Artifacts 下载 review-运行编号。只有 candidate-运行编号 表示候选已产生但完整预览未成功, 不能称为构建通过。只有 snapshot 产物不代表模型已运行。
6. 解压 review 包, 打开 review.html 看原文与建议、来源行和疑点; review.md 可用于文本审阅。点其中网页预览入口。若直接打开 HTML 不正常, 在解压目录运行 `python -m http.server 8980 --bind 127.0.0.1`, 再访问 `http://127.0.0.1:8980/review.html`; 结束后按 Ctrl+C。candidate.md 是候选全文, approved-snapshot.json 是批准原稿, snapshot.json 另外记录返回模型版本与用量。
7. **采用仍是人工操作, 没有自动应用或“一键接受”。** 先比较当前 Issue 和目标页与 approved-snapshot.json 中 issue、page_content 的原文。若已变化, 不直接覆盖; 重新逐段核对, 必要时生成新快照。全部同意且基准一致时可采用 candidate.md 的正文; 只同意部分时按 review.md 的 before/after 逐处修改, 保留其他原文。
8. 从最新 main 建立修改分支, 只编辑批准的目标文件, 按[直接修改与提交 PR 教程](../docs/contribute/editing.md)提交。PR 正文写明关联 Issue 和快照/处理运行链接, 在 Files changed 核对限定差异; 涉及网页结构时完成本站严格构建和预览。候选产物中的任何说明都不作为待执行命令。人工审核并合并后, 既有部署工作流才会发布; 本链路不替维护者点击合并。
9. 不采纳时保留原文件, 无需创建 PR。需要再次调用时重新做 snapshot 并明确批准; 不能点击 Re-run jobs 复用一次批准。人工完成后可自行回复/关闭 Issue, 本系统不会代发消息。

需要立即停止后续处理时, 在 Actions → 整理公开投稿 的右上角菜单选择 Disable workflow, 并对已开始的运行逐个 Cancel workflow。也可把仓库 Variable CONTRIBUTION_AI_ENABLED 设为 false 阻止新付费运行; 单改开关不会撤回已发出的请求。恢复时先核对账本 unknown/滞留状态, 不删除账本或重置锚点。

## 无密钥的本机逐步演示

仓库根目录运行下列命令, 输出目录放在仓库之外:

```sh
python -m scripts.contributions.demo --data-dir ../contribution-demo --port 8977
```

打开 `http://127.0.0.1:8977/`, 保留示例正文, 依次点击“提交演示投稿”→“生成免费快照”→“查看快照”; 复制显示的完整哈希, 勾选已审阅, 点击“批准此快照”→“生成模拟修改”, 然后打开对照与预览。模型计数在批准后仍为0, 生成后为1, 真实外部请求始终为0。页面上的“开始新一轮演示”可重做, 仅重置本机模拟场景, 与正式账本无关。

还可取消服务同意、输入错误哈希, 或在快照后点“模拟投稿随后被编辑”, 观察处理停止且没有模拟模型请求。演示只能处理固定的示例笔记入口, 不提供自由AI问答; 改掉依据文字可能让候选验证失败。

演示复用测试夹具和实际快照、批准、HMAC账本、输出校验及内存构建函数, 在进程中禁止发起 socket 连接, 不读取真实API密钥。GitHub运行/身份、内存Git图和固定模型响应都是模拟; 不能据此声称云端身份、持久存储或真实API通过。演示模块不被生产工作流调用, 没有给付费入口增加模拟/跳过校验开关。结束演示服务按 Ctrl+C, 已生成的审阅文件保留在指定输出目录。

公开仓库的日志和 Actions 产物都不是私密存储。摘要不输出正文, 审阅包只面向已确认能公开的材料; 程序还会拦截疑似凭据和运行密钥回显, 错误日志不输出供应商响应正文。此检测不能自动识别所有个人信息, 收件前的公开边界与维护者核对仍然必要。

## 验证范围

既有验证记录: 独立测试中的 DeepSeek 本地真实调用曾通过一次; OpenAI 与 Gemini 仅有模拟响应验证。上述记录不代表完整 GitHub 审批、持久账本和模型链路已通过云端验收。

运行 python -m unittest discover -s tests -p "test_contribution*.py"。测试使用模拟 GitHub Git 图、原子引用更新和三家模拟响应, 校验未获准的模型请求次数为零、材料变化、重复运行、并发额度、未知状态、恶意输出和合法预览。模型适配测试不等于真实服务验证。

本地还应运行严格构建并检查已有投稿页面交互。首次云端启用前先保持付费开关关闭, 验证 snapshot、维护者权限、账本初始化和产物下载; 再按明确授权做合成公开样例的最小真实调用。账户角色、分支保护、Actions 权限、实际 API 用量结构、延迟和账单均需在真实环境中确认。

官方接口依据: [DeepSeek](https://api-docs.deepseek.com/)、[GPT-6 Astra](https://developers.openai.com/api/docs/models/gpt-6-astra)、[Gemini generateContent](https://ai.google.dev/api/generate-content)、[Gemini 别名更新](https://ai.google.dev/gemini-api/docs/changelog)。模型与协议更新需审阅可信适配器和对应测试, 不接受投稿文字变更配置。
