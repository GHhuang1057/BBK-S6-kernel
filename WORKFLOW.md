# 逆向闭源厂商内核源码 — 完整工作流

> 本文档记录如何从一个**厂商 boot.img（闭源内核）** 逆向重建出**可编译、可运行、功能等价**的内核源码树。
> 本仓库（EEBBK S6 / P20H130, SM7150）就是用这套流程完成的实战案例。

## 适用场景

- 拿到一台安卓手机的 `boot.img` / `recovery.img`，需要对应内核源码
- 厂商（BBK/vivo/OPPO/realme 等）不公开内核源码，或公开版本不匹配
- 目标是：**版本一致、功能等价、可编译、可运行**（不是逐字节还原——那不可能）

## 总览：6 阶段

```
P0 可行性判定 → A1/A2 解包+符号 → A3 config还原 → A4 源码匹配
→ A5 符号核对 → A6 厂商代码逆向 → A7 编译 → A8 打包验证
```

---

## P0：可行性判定（30 分钟）

对 boot.img 做快速侦察，决定走哪条路：

```bash
# 1. 确认 boot.img 格式（传统 boot / vendor_boot / GKI）
# 头部 magic "ANDROID!"，header_version，page_size
python3 parse_bootimg.py boot.img out/    # 解析 header + 提取 kernel/ramdisk/dtb

# 2. 提取内核版本（linux_banner）
gzip -dc out/kernel > out/kernel.dec     # 解压内核
strings -a out/kernel.dec | grep -m1 'Linux version'

# 3. 检查关键配置（决定还原难度）
# CONFIG_IKCONFIG=y  → config.gz 可提取（最简单）
# CONFIG_KALLSYMS_ALL=y → 完整符号表可导出（核心资产）
grep -a 'IKCFG_ST' kernel.dec             # config.gz 魔数
grep -a 'CONFIG_KALLSYMS_ALL' out/config  # 符号表开关
```

**判定标准**：
- IKCONFIG=y + KALLSYMS_ALL=y → **路径 A（匹配官方源码）**，成功率极高
- 只有其一 → 路径 A 但需推断 config
- 都没有 → 路径 B（纯逆向重建），工作量大很多

---

## A1/A2：解包 + 导出符号表

### 提取 config.gz（如果 IKCONFIG 开启）

```bash
python3 - <<'EOF'
import gzip, io
data = open('kernel.dec','rb').read()
s = data.find(b'IKCFG_ST'); e = data.find(b'IKCFG_ED')
gz = gzip.GzipFile(fileobj=io.BytesIO(data[s+8:e]))
open('config','wb').write(gz.read())   # 这就是厂商的 .config，100% 精确
EOF
```

### 导出 kallsyms 符号表（如果 KALLSYMS_ALL 开启）

用 `vmlinux-to-elf`（从 kallsyms 表恢复符号并生成 ELF）：

```bash
pip install vmlinux-to-elf
vmlinux-to-elf kernel.dec vmlinux.symbols.elf   # 生成带符号 ELF
readelf -s vmlinux.symbols.elf > symbols.txt    # 完整符号表
```

**验证符号地址准确性**：用 `linux_banner` 交叉核对
（符号 VA - _text VA == 文件实际偏移，偏移差为 ELF 头大小则正确）。

---

## A3：确定平台与源码基线

- 内核版本如 `4.14.190` → 查 CAF（CodeAurora/CodeLinaro）对应分支
- 从 kernel 的 compatible 字符串确认 SoC（如 `qcom,sdmmagpie` = SM7150）
- **关键教训**：版本号直接决定 CAF 基线。
  - 本机案例：SM7150 有 `LA.UM.8.9`（4.14.117）和 `LA.UM.9.1`（4.14.190）两个分支
  - **必须匹配实际版本号**（4.14.190 → `LA.UM.9.1`），用错分支即使能编译也会开机卡死

```bash
# 在 CAF mirror 仓库里查版本号
git clone --filter=blob:none https://git.codelinaro.org/clo/la/kernel/msm-4.14.git
cd msm-4.14.git
git show <tag>:Makefile | grep -E '^(VERSION|PATCHLEVEL|SUBLEVEL)'
# 找 version==4.14.190 的 tag
```

---

## A4：匹配并获取源码

```bash
# 从 mirror 创建工作树
git worktree add /kernel/src/wt-<tag> <tag>
```

**符号链接问题（Windows 关键坑）**：
- 若 git 全局 `core.symlinks=false`（Windows 下 clone 常见），checkout 会把符号链接写成普通文本文件
- 内核树里符号链接很多（`include/uapi/linux/msm_ion.h` 等）
- 修复：`git -c core.symlinks=true checkout-index -f -a`

---

## A5：符号核对（量化厂商定制）

```bash
# boot.img 符号 vs 编译产物 System.map
cut -d, -f2 boot_symbols.csv | sort -u > /tmp/boot_syms.txt
awk '{print $3}' System.map | sort -u > /tmp/built_syms.txt
comm -23 /tmp/boot_syms.txt /tmp/built_syms.txt   # 厂商独有 = 需逆向的部分
```

**解读**：
- 共有符号占比高（>90%）→ 源码主体匹配，差异 = 厂商定制 + stable 补丁
- boot 独有符号里 `bbk_*`/`fts_*`/厂商前缀 = 闭源代码，需逆向补全

---

## A6：厂商代码逆向（Ghidra）

对 boot 独有的厂商函数做反编译：

```bash
# Ghidra headless 导出指定函数
analyzeHeadless <proj> <name> -import vmlinux.symbols.elf \
  -scriptPath <dir> -postScript ExportFuncs.java <outdir> <pattern...>
```

**反编译产物处理**：
- 质量好的（驱动结构清晰）→ 整理成可编译源码模块
- 标注"近似还原"置信度，别冒充逐字节源码
- 关键驱动的缺失项可从：官方驱动包（本机 FocalTech 就是用户提供的官方版）、主线内核、其它机型源码寻找

**实战案例（本仓库）**：
- 厂商用 FT8203 触控芯片，但 CAF 树/官方驱动默认配 FT8201
- 反编译原内核确认它**同时支持 0x8201/0x8203** → 给驱动加 0x8203 的 chip type 映射即解决
- 厂商驱动依赖的私有 API（如 `drm_panel_notifier`）→ 写 stub 让编译通过

---

## A7：编译（工具链是关键）

4.14 内核**必须用旧工具链**：

| 工具 | 版本 | 理由 |
|------|------|------|
| clang | 11.0.1 (AOSP 6443078) | 匹配厂商 clang 10.x，新 clang 编译 4.14 有兼容问题 |
| binutils | 2.27 (自编译) | 厂商用 GNU ld 2.27，新版 ld 有 `__crc_` ABS32 检查 |
| gcc-aarch64 | 13.x | 仅 compiler-check 用 |

**必须的源码修补**（现代工具链 vs 老内核）：
1. `scripts/gcc-wrapper.py`：Python2→3（Popen/print 语法）
2. `scripts/dtc/Makefile`：`+ -fcommon`（gcc13 默认 -fno-common）
3. `scripts/Makefile.build`：空 built-in.o 改 `touch`（新 ar 生成空归档 ld 不认）
4. trace 头文件 `-I$(src)`（clang 的 `#include "./x.h"` 行为差异）
5. 厂商依赖头文件 backport（如 `include/linux/haven/` 从 CAF 5.4）

```bash
export ARCH=arm64
export CROSS_COMPILE=<binutils-2.27>/bin/aarch64-linux-gnu-
make vendor/<platform>-perf_defconfig   # 或直接用厂商 config
make -j$(nproc) Image \
  REAL_CC=<clang>/bin/aarch64-linux-gnu-clang CLANG_TRIPLE=aarch64-linux-gnu-
```

---

## A8：打包 + 真机验证

**关键坑：原地替换法**（ABL 依赖固定偏移）：

```bash
# 不要重新打包（偏移会变，ABL 读错 dtb → 卡机）
# 在原镜像上原地替换 kernel 段：
python3 tools_inplace_replace.py recovery.img kernel.gz recovery_new.img
```

**要点**：
- 保持原镜像的 `kernel_size` 字段（ramdisk 偏移不变）
- gzip 用 `gzip -n`（去文件名/时间戳，ABL 对 gzip 头敏感）
- 大 DTB 段（recovery_dtbo 等）必须完整保留

**验证顺序**：
1. 先刷 recovery（TWRP）验证——不进系统，风险低
2. TWRP 能进 = 显示/存储/USB/充电 OK
3. 触控在 TWRP 里测（若原 TWRP 触控可用则硬件 OK，纯驱动问题）
4. 全部通过后再考虑 boot.img

---

## 工具与技能（AI Agent 可直接调用）

| 技能/工具 | 用途 |
|-----------|------|
| `reverse-skill-router` | 逆向任务路由（已加载） |
| `ghidra-reverse` / `ghidra-rpc` | 反编译厂商函数 |
| `binary-diff` | 跨版本符号迁移/差分 |
| `patch-diff-exploit` | 补丁→利用（N-day） |
| `vmlinux-to-elf` | 从 kallsyms 恢复符号 |
| CAF mirror (`git.codelinaro.org`) | 内核源码源 |

**AI Agent 提示词模板**：
> 从 boot.img 交付一棵"可用"的 Android 内核源码树：解包→提config/符号→匹配CAF基线→符号diff定位厂商代码→Ghidra逆向补全→旧工具链编译→原地替换打包→TWRP验证。

---

## 本仓库实战数据

| 项 | 值 |
|----|-----|
| 设备 | EEBBK S6 (P20H130) |
| SoC | Qualcomm SM7150 (sdmmagpie) |
| 内核 | 4.14.190 |
| CAF 基线 | LA.UM.9.1.c25-01800-SMxxx0.QSSI12c26.0 |
| 厂商定制 | ~190 函数（bbk_*/fts_*/hall/VIP/ramext） |
| 触控 | FocalTech FT8203（默认驱动配 FT8201，需加 0x8203 映射）|
| 结果 | ✅ 编译通过，真机 TWRP 验证：显示/存储/充电/USB/触控 全部正常 |

## 局限性（诚实说明）

1. **不保证逐字节还原**——厂商闭源代码是"功能等价近似"
2. **inline-crypt 等厂商 backport** 若 CAF 树没有 Kconfig，无法通过纯 CAF 树还原
3. 逆向出的驱动可能有细微行为差异，需真机验证
4. 涉及厂商私有代码（haven/trusted touch 等）用 stub 绕过，功能可能受限
