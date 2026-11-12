<div align="center">

<img src="assets/icon.png" alt="麦麦绘图插件图标" width="128" height="128">

# 麦麦绘图

![Plugin Version](https://img.shields.io/badge/Plugin-2.2.1-informational.svg) ![MaiBot](https://img.shields.io/badge/MaiBot-1.3.6%E2%80%931.4.99-blue.svg) ![MaiBot Plugin SDK](https://img.shields.io/badge/Plugin%20SDK-2.12.0%E2%80%932.22.1-blueviolet.svg) ![License](https://img.shields.io/badge/License-AGPL--3.0-green.svg)

**❤️为 MaiBot 提供多平台聚合绘图能力，内置现代化 WebUI 工作台与聊天指令支持❤️**

</div>

本仓库是 [WhiteCloudOL/maimai-drawpic-plugin](https://github.com/WhiteCloudOL/maimai-drawpic-plugin) 的人物参考图增强 fork，保留原插件 ID `maimai-drawpic-plugin` 和实例数据。

## 本 fork 的全部改动

- **人物参考图设置**：新增「偏好与预设 → 人物参考图」，可上传、预览和移除同一人物的 1～3 张照片，每张不超过 6 MiB。图片上传、移除后立即保存；人物姓名、昵称和开关点击「保存全部设置」生效，切换分类保留草稿。
- **本人出镜自动附图**：开启后，根据本次绘图描述识别自拍、本人穿搭和本人入镜的合照等，自动附带真实参考图并使用图生图。纯风景、食物、物品及明确的其他人物照保持原流程，不会强行加入本人。
- **各入口共用**：AI 绘图工具、风格绘图、工作台及其他插件通过麦麦绘图提交的请求共用此逻辑，不依赖麦生活。工具说明同步提醒模型在绘图描述中明确人物身份。
- **保持人物身份**：提示词约束脸型、五官、肤色、发色、瞳色、体貌与年龄感，服装、姿势、表情和场景按要求变化；合照只约束该人物。已有编辑源图继续保留，与参考图内容完全相同的图片去重，并保留调用方提供的原图 URL。
- **提交前检查**：判定失败、缺少参考图、模型不支持图生图或源图数量超限时，在创建生图任务和扣绘图额度前拒绝，不静默改为无参考图生成。只接受公网源图 URL 的模型无法直接使用未托管的本地参考图。
- **参考图长期保存**：图片保存在实例插件数据目录的 `persona_references/`，不受普通上传缓存的过期清理影响；开关等配置仍在 `workspace_settings.json`。上传和删除带修订号检查，避免多个页面互相覆盖。
- **保留原有命令语义**：强制 `/绘图 文生图` 或 NAI 文生图遇到本人出镜会提示模式冲突，请改用普通绘图或风格绘图；强制图生图命令仍需附带或引用真实源图。相同 `request_id` 优先恢复原任务，不会因参考图更新而再次生成。
- **配置与文档**：新增设置包含中、英、日、韩文案；配置版本提升至 `2.46.0`，插件版本暂保留 `2.2.1`；仓库和更新来源改为本 fork。

**启用方法**：打开「偏好与预设 → 人物参考图」，上传照片，填写人物姓名及常用昵称，开启自动使用并保存。姓名留空沿用 MaiBot 的机器人昵称。所选生图模型须支持图生图及全部参考图数量。

人物判定默认使用 MaiBot 的 `utils` 模型任务，每次新绘图调用一次，也可选择 `replyer`、`planner` 或 `vlm`；判断读取原始绘图描述，避免风格模板里的“同一人物”等文字误触发。请在描述中明确人物姓名或“机器人本人”。语义判断依赖模型，参考图也不能保证每次生成的脸完全一致。

## 在线安装与切换来源

本 fork 尚未加入官方插件市场，市场中原版「麦麦绘图」的安装、更新按钮不能当作本 fork 的入口。核对 MaiBot 1.4.3 当前实现，插件页面提供市场安装和 ZIP 安装，没有任意填写 GitHub 仓库地址的安装框；ZIP 安装同 ID 插件时要求先卸载。

### 已装原版，切换为本 fork（保留现有目录）

先在 MaiBot 页面停止对应机器人，备份现有插件目录与实例的插件数据目录，再进入 1Panel 的 MaiBot **容器终端**。以下命令均在现有 `maimai-drawpic-plugin` 插件目录内执行。

先确认目录是 Git 仓库且没有本地代码修改：

```bash
git status --short
```

没有输出时继续；有修改或提示不是 Git 仓库时先停止，不执行强制重置。Git 安装可直接切换来源并快进更新，无需卸载：

```bash
git remote set-url origin https://github.com/Kanawooo/maimai-drawpic-plugin.git
git pull --ff-only origin main
```

完成后重新启动机器人或重载插件，打开「偏好与预设」确认出现「人物参考图」。两者插件 ID 相同，继续使用原来的实例数据目录；代理、插件开关所在的 `config.toml` 也保留在现有目录中。首次切换版本号仍可能显示 `2.2.1`，以新增页面和实际提交为准。

若原安装没有 `.git`，不要直接删除旧目录。可先备份，再通过 ZIP 安装切换：下载 [本 fork 的 main 源码 ZIP](https://github.com/Kanawooo/maimai-drawpic-plugin/archive/refs/heads/main.zip)，卸载旧插件后在插件页面的「ZIP 安装」上传，恢复原 `config.toml`，重新加载。保留实例数据目录中的平台配置、风格、额度与参考图。源码 ZIP 不含 `.git`，之后不能直接运行 `git pull`；继续从本 fork 获取 ZIP 更新，或切换为 Git 安装。

### 尚未安装

在 MaiBot 实例的 `plugins` 目录内执行，让服务器直接从 GitHub 下载：

```bash
git clone --branch main https://github.com/Kanawooo/maimai-drawpic-plugin.git
```

然后重新加载插件。仅使用网页时，也可下载上面的 ZIP，通过「ZIP 安装」上传。

## 同步上游并保留人物参考图

后续更新分两步：**先合并到你的 GitHub fork，再让机器人更新这个 fork**。参考图功能作为独立提交保留在本仓库的 `main` 中；正常合并上游会保留这些提交，若修改冲突则需处理后再继续。

1. 打开 [Kanawooo/maimai-drawpic-plugin](https://github.com/Kanawooo/maimai-drawpic-plugin)，选择 `main`。
2. 上游有更新时点击 **Sync fork → Update branch**。有冲突时停止自动同步，通过 PR 解决冲突，保留人物参考图相关逻辑后再合并。不要选择丢弃本 fork 提交的 **Discard commits** 或强制覆盖。
3. 合并后停止对应机器人，在服务器插件目录执行：

   ```bash
   git pull --ff-only origin main
   ```

4. 重新加载插件，核对参考图设置仍在。参考图和配置属于实例数据，不需要重新上传；合并代码仍需检查人物判断、自动附图和设置页面是否正常。

也可以在装有 GitHub CLI 的电脑上执行 `gh repo sync Kanawooo/maimai-drawpic-plugin --branch main`，不添加 `--force`；发生冲突时会停止。[GitHub 官方同步说明](https://docs.github.com/en/pull-requests/how-tos/work-with-forks/syncing-a-fork)

服务器的 `origin` 应一直指向本 fork。MaiBot 市场详情优先使用市场元数据，可能仍指向原作者仓库；更新本 fork 时使用上述 Git 命令，不从原版市场卡片更新或重装。

---

## 原插件功能

- **双端交互支持**：支持聊天指令与可视化 WebUI 双向操作，自由输入提示词、上传参考图并切换画风预设
- **多平台灵活管理**：支持多平台及同平台多实例配置，密钥、地址、参数完全独立，支持首选模型与按序备用切换
- **任务看板与排查**：后台异步执行，支持随时切页查询进度、浏览原图与失败日志，大图生成无需死守页面
- **精细化控制与模板**：可视化配置群聊／私聊额度、内容审查规则与黑白名单，内置风格模板支持一键复用
- **开箱即用的联动 API**：提供统一的任务调用接口与独立 `DrawingClient` 实现，方便第三方插件快速接入，详见[插件联动](./docs/integration.md)

## 🩷 问题反馈&功能建议
| 方式 | 联系 |
| :--: | :--: |
| 本 fork 的 Github Issue | [跳转](https://github.com/Kanawooo/maimai-drawpic-plugin/issues) |
| QQ群 | [637174573](https://qm.qq.com/q/3f2bdkDsyW) |


## ✨ 工作台预览

![麦麦绘图插件扩展WebUI](assets/previews/workspace-desktop.png)

<details>
<summary>📱 查看移动端预览</summary>

<img src="assets/previews/workspace-mobile.png" alt="麦麦绘图移动端工作台" width="390">

</details>

---

## ⚡ 快速导航
[安装说明](#在线安装与切换来源) · [保留功能同步上游](#同步上游并保留人物参考图) · [快速上手](#-快速上手) · [支持平台](#-支持平台) · [聊天命令](#-聊天命令) · [配置与特性](#-配置与高级特性) · [常见问题](#-常见问题)


---

## 🚀 快速上手

首次使用前，请准备好绘图服务的 API Key 与可用模型（ComfyUI 用户需准备好 API 格式工作流）。

1. **添加平台**：进入 WebUI **绘图平台 → 添加平台**，选择平台类型
2. **配置连接**：设置自定义平台名称（如“日常创作”），填入 API Key、服务地址与可用模型 ID，保存后即刻生效
3. **文生图测试**：切换至 **开始创作 → 文生图**，输入 Prompt，挑选模型并点击 **开始绘图**
4. **查看成果**：在创作区或 **绘图任务** 列表查看进度与原图。若需发送到群聊，展开表单底部的发送选项即可

> 图生图支持上传参考图并在提示词中描述修改点。若模型要求公网 URL，需先将源图托管至可访问的公网地址。[完整使用指南 →](docs/usage.md)

---

## 🎨 支持平台

各平台均支持添加多个命名实例，按需启用：

| 平台 | 文生图 / 图生图 | 特性与主要限制 |
| :--- | :--- | :--- |
| **OpenAI / 兼容接口** | 视模型支持 | 支持各类兼容 OpenAI 规范的中转站与直连 |
| **Google Gemini** | 视模型支持 | 支持的模型参考图数量有所不同 |
| **智谱 AI** | 文生图 | 默认内置模型 `glm-image` |
| **MiniMax** | 全部支持 | 默认 `MiniMax-H3-Image`；image-01 支持主体参考 |
| **阿里百炼** | 视模型支持 | 可灵/Vidu 等编辑类模型要求原图提供公网 URL |
| **火山引擎** | 视模型支持 | 适配 Seedream 体系模型与校验能力 |
| **硅基流动** | 视模型支持 | 生成与图像编辑模型通常独立区分 |
| **NovelAI / NovelAPI** | 全部支持 | 默认开启反向词与多角色处理；图生图参考图为 1 张 |
| **Agnes AI** | 全部支持 | Image 2.0 采用像素尺寸；2.1 / 2.5 支持 1K–4K 及常用比例 |
| **ComfyUI** | 视工作流支持 | **必须**导出并使用 API 格式工作流 JSON |

详细配置与各家额度限制请查阅 [各平台最小配置与限制说明](docs/platforms.md)

---

## 💬 聊天命令

可在聊天中直接使用快捷指令发起作画或调整状态：

```text
/绘图 帮助
/绘图 模型
/绘图 文生图 夜晚的海边灯塔，水彩插画
/绘图 图生图 保留主体，把背景改成樱花树林 [附带图片或回复原图]
/绘图 风格 水彩 一座森林小屋
/绘图 状态
```

> [!NOTE]
> 图生图需附带图片或引用含有图片的消息。更多高级用法（如反向词过滤、NAI 专用语法、额度限制、英文别名等）详见 [完整命令用法表](docs/usage.md#聊天命令)。

---

## ⚙️ 配置与高级特性

WebUI 偏好设置采用标签页分类，右下角统一保存修改，修改项支持单击撤回图标快速重置。

- **模型与预设覆盖**：支持按模型覆盖分辨率、OpenAI 兼容接口模式，并配置平台扩展参数；支持常用尺寸下拉与自定义宽高
- **风格模板**：模板中 `{prompt}` 与 `{negative_prompt}` 为占位符，支持一键注入固定画风，未指定风格时自动继承默认预设
- **会话历史同步**：可在「通用配置」开启 *生成图片同步到会话历史*，开启后发至聊天的图片可供视觉 Planner 查看
- **权限与审核**：内置提示词与图片双重审查，支持 `vlm` / `planner` / `replyer` 模型，支持分别设置群聊／私聊黑白名单
- **缓存与日志**：在 MaiBot 宿主插件配置页可限制图片缓存（默认 300MB）与日志容量（默认 10MB），重要生成图建议本地另存

配置与预设均存储为标准 UTF-8 JSON，高级玩法详见 [手动编辑配置指南](docs/manual-configuration.md)。

---

## ❓ 常见问题

- **模型列表下拉为空？**<br>
  检查该平台是否已开启胶囊开关，并确认填写的模型 ID 与账号实际开通的模型权限一致
- **图生图提示“能力校验不通过”？**<br>
  所选模型可能不支持多图输入，或部分国内平台要求参考图必须是公网 HTTP/HTTPS 直链
- **请求超时或任务状态未更新？**<br>
  工作台取消仅终止本地等待，上游执行与计费以服务商账单为准；可先前往服务商控制台核对任务
- **图片无法下载 / 报 IP 校验异常？**<br>
  使用 TUN/Fake-IP 代理或内网私有图床时，在「通用配置」开启 *忽略图片地址 IP 校验*
- **表单填写内容丢失？**<br>
  偏好设置切换分类会保留草稿；离开未保存的配置页会提示确认。已提交任务可在“绘图任务”中查询；提交回执未确认时使用“恢复原提交”找回原任务
- **ComfyUI 报错无法执行？**<br>
  使用 ComfyUI 菜单中的「导出（API 格式）」保存 JSON。默认放在 `MaiBot\data\plugins\maimai-drawpic-plugin\workflows`，文生图设置填写 `data/workflows/t2i.json`，图生图填写 `data/workflows/i2i.json`；`MaiBot` 为主程序根目录。详见 [ComfyUI 配置](docs/platforms.md#comfyui-本地工作流)

---

## 📚 完整文档与扩展

- **用户指南**：[完整使用指南](docs/usage.md) ｜ [平台接入配置](docs/platforms.md) ｜ [配置与数据迁移](docs/configuration.md)
- **开发者接入**：[插件联动与 DrawingClient](docs/integration.md) ｜ [独立客户端](clients/README.md)
- **适配器支持**：[官方 QQ 机器人与 SnowLuma 适配说明](docs/qq-adapters.md)

---

## 开源协议

采用 [AGPL-3.0](LICENSE) 协议发布
