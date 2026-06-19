---
name: fix-errors
description: 修复 Rust 代码库中的编译错误、代码检查（lint）问题与测试失败，覆盖常见的 rustc / clippy 错误、WebAssembly（WASM）专属约束，以及运行定向测试。当用户遇到构建错误、clippy 或 fmt 失败、测试失败，或需要在提交 PR 前运行预检查时使用。
---

# fix-errors

修复 Rust 代码库中的编译错误、代码检查问题和测试失败。

## 概述

本技能用于解决开发过程中常见的各类问题，包括：
- 编译错误（未使用的导入、类型不匹配等）
- 代码检查失败（clippy 警告）
- 格式违规
- WASM 特定错误
- 测试失败

在打开或更新拉取请求之前，所有预提交检查必须通过。

## 预提交检查

如果项目提供了统一的预提交脚本，一次性运行所有检查：

```bash
./script/presubmit
```

如果没有预提交脚本，则手动运行：代码格式化、代码检查和全部测试。

### 单独检查

调试特定问题时分开运行：

**Rust 格式化：**
```bash
cargo fmt -- --check
```

**Clippy（完整工作区）：**
```bash
cargo clippy --workspace --all-targets --all-features --tests -- -D warnings
```

如果工作区中有需要从 clippy 中排除的 crate，对这些 crate 使用 `--exclude <crate_name>`，然后使用 `-p <crate_name> --all-targets --tests -- -D warnings` 单独运行。

**WASM Clippy：**
```bash
cargo clippy --target wasm32-unknown-unknown --profile release-wasm-debug_assertions --no-deps
```

**全部测试：**
```bash
cargo nextest run --no-fail-fast --workspace
```

如果工作区使用 `cargo test` 而非 `cargo nextest`，请相应替换。

**文档测试：**
```bash
cargo test --doc
```

## 运行指定测试

**单个包：**
```bash
cargo nextest run -p <package_name>
```

**按测试名称过滤：**
```bash
cargo nextest run -E 'test(<substring>)'
```

**指定包并过滤：**
```bash
cargo nextest run -p <package_name> -E 'test(<substring>)'
```

**带输出（不捕获）：**
```bash
cargo nextest run -p <package> --nocapture
```

## 常见错误类型

### 未使用的导入
删除编译器标识出的未使用 `use` 语句。

### 未使用的常量
删除已定义但从未使用的常量。

### 未知导入
为未定义的类型添加正确的 `use` 语句。搜索代码库以找到正确的模块路径。

### 类型不匹配
更新函数调用以传递正确类型的参数。常见修复：
- 当需要 `&str` 时使用 `.as_str()` 而不是 `.clone()`
- 当需要引用时使用 `&value`
- 当需要 `String` 但提供了 `&str` 时使用 `.to_string()`

### 结构体字段变更
当结构体新增或删除字段时，更新所有构造或解构该结构体的位置：
- 结构体初始化
- 模式匹配（`match`、`if let`）
- 解构赋值

### 函数签名变更
当函数新增参数时，更新所有调用点以提供新参数：
- 对于 `bool` 参数：根据上下文传入 `true` 或 `false`
- 对于 `Option<T>` 参数：传入 `None` 作为默认值，或根据需要传入 `Some(value)`

### 枚举变体变更
添加新枚举变体时，更新穷尽 `match` 语句：
- 添加新的 match 分支并做相应处理
- 镜像类似变体的实现模式

### 错误的 trait 实现
修复返回错误类型或不满足 trait 约束的 trait 实现。

### WASM 特定错误

WASM 构建（`wasm32-unknown-unknown` 目标）不支持文件系统操作。使用文件系统 API 的代码必须隐藏在特性标志后面，例如 `local_fs` 或等效标志。

**常见 WASM 错误：**
- 仅非 WASM 构建使用的代码产生死代码警告
- 仅在启用本地文件系统特性时才相关的未使用代码
- 需要文件系统访问的测试

**修复：**

**将测试隐藏在特性标志后面：**
```rust
#[test]
#[cfg(feature = "local_fs")]
fn test_find_git_repo_with_worktree() {
    // 使用文件系统操作的测试
}
```

**有条件地允许仅在特性启用时使用的类型产生死代码：**
```rust
#[cfg_attr(not(feature = "local_fs"), allow(dead_code))]
#[derive(Clone, EnumDiscriminants, Serialize)]
pub enum ExampleType {
    // 仅在特性启用时使用的变体
    Variant1,
    Variant2,
    Variant3,
}
```

通过运行以下命令发现 WASM 错误：

```bash
cargo clippy --target wasm32-unknown-unknown --profile release-wasm-debug_assertions --no-deps
```

## 最佳实践

**修复前：**
- 阅读完整错误信息以理解根本原因
- 检查多个错误是否相关（修复一个可能解决其他错误）
- 对于 trait/类型错误，验证你理解预期类型与实际类型
- 对于 WASM 错误，检查代码是否需要隐藏在本地文件系统特性标志后面

**修复时：**
- 同时存在多个问题时，一次修复一种错误类型
- 频繁运行 `cargo check` 以验证修复
- 对于 WASM 错误，运行 WASM clippy 验证修复
- 对于复杂更改，修复后运行相关测试

**修复后：**
- 推送前始终运行 `cargo fmt` 和 `cargo clippy`
- 在打开或更新 PR 前运行完整的预提交脚本或等效检查。如需详细指导，使用 `create-pr` 技能
- 验证所修改区域的测试通过
