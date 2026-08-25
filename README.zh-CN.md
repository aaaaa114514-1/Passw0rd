# P@ssw0rd

P@ssw0rd 是一个仅面向 Windows 本机环境的密码管理工具。它提供加密密码库、现代 Qt 桌面界面、亮色/暗色主题、自定义背景图以及中英文界面切换。

[English README](README.md)

## 功能

- 使用主密码保护本地加密密码库。
- 首次运行创建密码库，之后每次启动均需输入主密码解锁。
- 支持无限次解锁尝试；按设计不提供密码重置或找回功能。
- 支持条目的新建、查看、编辑、搜索、筛选、排序与删除。
- 每条记录可保存账户名称、用户名、手机号、邮箱、网址、密码、分类、标签和备注。
- 用户名、手机号、邮箱、网址和密码支持一键复制。
- 支持按分类筛选；未填写分类的条目可使用“未分类”筛选。
- 支持点击账户、身份信息、分类表头排序：首次点击升序，再次点击降序。
- 支持亮色/暗色主题、自定义背景图与中文/英文切换。
- 支持调整账户列表与详情面板的宽度，并提供顶部动画成功提示。
- 使用提供的图标作为 Windows 程序图标、窗口图标和主界面标题图标。

## 安全模型

P@ssw0rd 用于本机 Windows 密码库，不提供云同步、远程服务、浏览器扩展或密码找回功能。

- 主密码不会以明文形式保存。
- 程序会生成 32 字节随机盐值，并使用 PBKDF2-HMAC-SHA256、600,000 次迭代派生 64 字节密钥材料。
- 派生材料的一部分通过 HMAC-SHA256 用于验证主密码。
- 另一部分用作 AES-256-GCM 加密密钥。
- 每个条目会被序列化为一个加密载荷，并使用独立随机的 12 字节 nonce。
- 账户名称、身份信息、网址、密码、分类、标签和备注等敏感字段均会加密后存储。
- SQLite 数据库保存加密二进制数据和时间戳，不保存明文条目字段。
- 修改主密码时，程序会先验证当前主密码，再基于新的密钥材料重新加密全部条目。
- 锁定密码库或关闭程序后，内存会释放当前会话密钥和 SQLite 连接。

> **重要：** 程序不提供主密码找回机制。遗失主密码后，现有数据无法解密。对于重要密码库，请妥善备份应用数据目录。

## 数据位置

默认数据目录：

```text
%LocalAppData%\P@ssw0rd
```

目录内包含：

- `vault.db`：包含加密条目载荷的 SQLite 数据库。
- `vault_config.json`：盐值、PBKDF2 参数和密码验证材料，不包含主密码。
- `ui_preferences.json`：主题、语言、背景图路径等非敏感界面偏好。

这些文件不应提交到版本控制，项目的 `.gitignore` 已将其排除。

## 环境要求

### 运行发布版

- Windows 10 或更高版本，64 位。
- 发布的单文件 exe 不要求额外安装 Python 或 PySide6 运行时。

### 从源码开发

- Windows 10 或更高版本。
- 建议使用 Python 3.12。
- Git。

## 快速开始

### 运行发布版

发布完成后，运行：

```text
publish\P@ssw0rd.exe
```

首次启动时请输入并确认一个非空主密码。之后每次启动均使用该主密码解锁密码库。

### 从源码运行

在仓库目录中创建隔离虚拟环境：

```powershell
python -m venv .venv
python -m pip --python .venv install -r requirements.txt
.\.venv\Scripts\python.exe src\qt_app.py
```

项目依赖只安装在 `.venv` 中，不需要全局安装 Python 包。

## 测试

在仓库根目录运行：

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp .\test-tmp
```

当前测试覆盖密码库初始化、错误密码拒绝、磁盘加密载荷、条目持久化、主密码轮换、输入验证和 UI 偏好持久化。

## 构建单文件 Windows 可执行文件

发布版会嵌入 Windows ICO 图标和应用标题旁的 PNG 图标。

```powershell
.\.venv\Scripts\pyinstaller.exe `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --name "P@ssw0rd" `
  --icon "D:\desktop\Code\aaaaa\dsh\P@ssw0rd\icon\favicon.ico" `
  --add-data "D:\desktop\Code\aaaaa\dsh\P@ssw0rd\icon;icon" `
  --distpath publish `
  --workpath build `
  --specpath build `
  src\qt_app.py
```

构建结果为 `publish\P@ssw0rd.exe`。`build/`、`publish/` 和 PyInstaller 生成的 spec 文件均被 `.gitignore` 排除。

如果仓库克隆到其他路径，请将命令中的两个绝对图标路径替换为该副本对应的绝对路径。

## 界面说明

- 点击标题栏中的太阳/月亮图标切换亮色和暗色主题。
- 通过 **设置** 修改外观、语言、背景图和主密码。
- 选中一行可查看账户详情；列表仅支持整行单选。
- 点击表头可以对当前可见的筛选结果排序。
- 拖动中间分隔条可以调整列表与详情面板的宽度。
- 复制字段后，窗口顶部会显示带勾选图标的自动消失提示。

## 项目结构

```text
.
├── icon/                  # 程序 ICO 和界面 PNG 图标资源
├── src/
│   ├── qt_app.py          # PySide6 桌面界面及打包资源处理
│   ├── vault.py           # 加密 SQLite 密码库和主密码服务
│   ├── preferences.py     # 非敏感界面偏好持久化
│   └── app.py             # 保留的早期 Tk 界面源码
├── tests/
│   ├── test_vault.py      # 密码库行为和加密测试
│   └── test_preferences.py
├── requirements.txt
├── pyproject.toml
├── WORKLOG.md             # 按时间归档的开发日志
└── README.md
```

## 范围与限制

本项目定位为 Windows 本机密码管理工具。在将其作为重要凭据的唯一保存位置前，请确认其本地化设计、威胁模型与恢复限制符合你的需求。

- 未实现同步、共享或多设备访问。
- 未实现自动清空剪贴板。
- 尚未实现密码生成器。
- 尚未实现导入/导出。
- 密码库安全性依赖于主密码强度，以及承载它的 Windows 账户和设备的安全性。

## 许可证

当前尚未选择许可证。若要分发项目，请先补充明确的许可证文件。
