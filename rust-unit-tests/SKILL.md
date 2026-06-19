---
name: rust-unit-tests
description: 编写、改进并运行 Rust 单元测试，覆盖 crate 级单元测试、异步测试、特性开关（feature-flag）行为、通用辅助函数，以及工作区级别的测试命令。当用户想新增或完善单元测试、排查测试失败，或为 Rust 项目设定测试规范时使用。
---

# Rust 单元测试

## 适用范围
- 本技能专注于 crate 级别的单元测试。
- 推荐增量式、范围清晰的测试，每个用例只验证单个函数或单个行为。

## 单元测试存放位置
- 将单元测试放在单独的文件中，文件命名使用 `${filename}_tests.rs` 或 `mod_test.rs`。
- 在对应源文件末尾引入测试模块：

```rust
#[cfg(test)]
#[path = "filename_tests.rs"] // 或 "mod_test.rs"
mod tests;
```

## 编写高质量测试
- 使用描述性的函数名：`fn parses_utf8_sequence_when_valid()`。
- 优先使用 `assert_eq!`/`assert_ne!`，而不是 `assert!`，以获得更清晰的差异输出。
- 仅在 API 明确约定 panic 语义时才使用 `#[should_panic]`。
- 尽量减少全局状态；通过 trait/构造函数注入依赖，使逻辑无需大量 mock 即可测试。
- 添加枚举或扩展行为时，优先对被测试代码使用穷尽匹配，并在测试中镜像所有分支。
- 注意锁模式：避免在同一个调用栈中多次获取同一对象的锁。

## 异步代码与特性开关
- 对于需要运行时的异步逻辑，使用 `#[tokio::test]`。
- 优先使用运行时特性检查，而不是 `#[cfg(...)]`，这样无需重新编译即可切换行为：

```rust
if my_crate::features::FeatureFlag::X.is_enabled() {
    // 特性开关控制的代码
}
```

## 快速测试框架（应用/模型测试）
许多 UI 或模型驱动的 crate 提供用于确定性单元测试的测试框架。在项目中尽量使用类似 `App::test` 的等效方式。通用模式如下：

```rust
use mycrate::App;
use mycrate::test_util::{initialize_app_for_terminal_view, add_window_with_terminal};

#[test]
fn example() {
    App::test((), |mut app| async move {
        initialize_app_for_terminal_view(&mut app);
        let term = add_window_with_terminal(&mut app, None);

        // 执行
        term.update(&mut app, |view, _ctx| {
            view.model.lock().simulate_block("ls", "out");
        });

        // 断言
        term.read(&app, |view, _ctx| {
            assert!(view.model.lock().block_list().len() > 0);
        });
    })
}
```

如果项目没有这样的框架，则使用标准 Rust 测试模式，直接调用函数并断言。

## 常用辅助工具
- 模型快捷方式：`Model::mock(..)`、`.simulate_block(..)`、`.finish_block()`、`.simulate_cmd(..)`。
- 构建器用于聚焦测试：`model::test_utils::{TestBlockListBuilder, TestBlockBuilder}`。
- 用于 IO 密集型代码的虚拟文件系统：

```rust
use virtual_fs::{VirtualFS, Stub};
VirtualFS::test("case", |_dirs, mut fs| {
    fs.with_files(vec![Stub::FileWithContent("path/file.txt", "contents")]);
    // 执行逻辑并断言
});
```

- 特性标记（作用域内）：

```rust
use mycrate::features::FeatureFlag;
let _flag = FeatureFlag::CreatingSharedSessions.override_enabled(true);
```

- UI 数值断言（行数）：

```rust
assert_lines_approx_eq!(actual_lines, EXPECTED_HEIGHT);
```

- 并发：保持 `model.lock()` 的作用域尽可能小；避免在同一调用链中出现嵌套/重入锁。
- 异步需求：在需要真实运行时时使用 `#[tokio::test]`；否则优先使用应用测试框架或标准 `#[test]`。
- 涉及全局/外部状态的测试：考虑使用 `serial_test` 的 `#[serial]`，或改用本地 mock 而非并行。

## 运行单元测试
- 工作区（并行）：
```bash
cargo nextest run --no-fail-fast --workspace
```
- 单个 crate：
```bash
cargo nextest run -p <crate_name>
```
- 单个测试（按名称过滤）：
```bash
cargo nextest run -E 'test(<substring>)'
```
- 文档测试：
```bash
cargo test --doc
```

## 代码检查与格式化
提交更改前运行：
```bash
cargo fmt
cargo clippy --workspace --all-targets --all-features --tests -- -D warnings
```

在提交 PR 前，运行项目提供的预提交脚本或等效的 CI 检查。
