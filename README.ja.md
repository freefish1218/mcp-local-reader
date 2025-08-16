# MCP-LOCAL-Reader

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP](https://img.shields.io/badge/FastMCP-2.8%2B-green.svg)](https://github.com/jlowin/fastmcp)

[English](README.md) | [中文版](README_zh.md) | [Français](README_fr.md) | [Deutsch](README_de.md)

**AI対応ドキュメントコンバーター** - あらゆるローカルファイルをAI最適化されたMarkdown形式に変換し、Claude Desktop、Claude Code、その他のMCPクライアントとのシームレスな統合を実現します。

**インテリジェント文書処理** - PDF、Officeドキュメント、画像などの高度な解析による高性能ローカルファイルコンテンツ抽出。複雑なドキュメントを自動的にクリーンで構造化されたMarkdownに変換し、AIモデルが容易に理解・処理できるようにします。

## 機能

### 📄 **AI最適化ファイル処理**
- **PDFドキュメント**: PyMuPDF4LLMによる高度解析 → クリーンなMarkdown出力
- **Officeスイート**: Word、Excel、PowerPoint → 構造化されたテーブルとテキスト
- **OpenDocument**: ODT、ODS、ODP → 標準化されたMarkdown形式
- **テキスト・データ**: Markdown、JSON、CSV、EPUB → AI可読性の向上
- **画像**: OCRテキスト認識 → 検索可能なMarkdownコンテンツ
- **アーカイブ**: スマート抽出 → 整理されたドキュメントコレクション

### 🚀 **インテリジェントパフォーマンス**
- **スマートキャッシュ**: 処理済みファイルを記憶し、即座に再アクセス
- **遅延読み込み**: 必要なコンポーネントのみを読み込み - 80%高速起動
- **並行処理**: 複数ファイルの同時処理
- **リソース最適化**: スマートリミットによるシステム過負荷防止

### 🔒 **セキュリティ・制御**
- **ディレクトリ権限**: 特定ディレクトリへのアクセス制限
- **パス検証**: 絶対パス要件による安全なファイルアクセス
- **ファイルサイズ制限**: 設定可能なサイズ制限によるDoS攻撃防止
- **ローカルファースト**: データは端末を離れません - 完全なプライバシー

## クイックスタート

### 前提条件

- Python 3.11+
- [uvパッケージマネージャー](https://docs.astral.sh/uv/)

### インストール

#### オプション1: ワンコマンドセットアップ（推奨）

```bash
# クローンと自動設定
git clone https://github.com/freefish1218/mcp-local-reader.git
cd mcp-local-reader
chmod +x install.sh && ./install.sh
```

インストーラーが3つのインストールモードをガイドします：

1. **最小**: PDFと基本テキストファイルのみ（最小フットプリント）
2. **標準**: Officeドキュメントサポート、OCRなし（推奨）
3. **完全**: OCRとアーカイブ処理を含むすべての機能

#### オプション2: 手動インストール

```bash
# uvパッケージマネージャーをインストール
curl -LsSf https://astral.sh/uv/install.sh | sh

# プロジェクトセットアップ
git clone https://github.com/freefish1218/mcp-local-reader.git
cd mcp-local-reader
uv sync

# 環境設定
cp env.example .env
# 設定で.envを編集

# サーバー起動
uv run python run_mcp_server.py
```

### Claude Desktop設定

#### 自動設定
```bash
chmod +x configure_claude.sh && ./configure_claude.sh
```

#### 手動設定
`~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) または同等のファイルを編集：

```json
{
  "mcpServers": {
    "mcp-local-reader": {
      "command": "uv",
      "args": [
        "run", 
        "python", 
        "/absolute/path/to/mcp-local-reader/run_mcp_server.py"
      ],
      "env": {
        "LOCAL_FILE_ALLOWED_DIRECTORIES": "/Users/username/Documents,/Users/username/Downloads"
      }
    }
  }
}
```

### Claude Code設定

`.claude/claude_config.json`に追加：
```json
{
  "mcpServers": {
    "mcp-local-reader": {
      "command": "uv",
      "args": [
        "run", 
        "python", 
        "/absolute/path/to/mcp-local-reader/run_mcp_server.py"
      ],
      "env": {
        "LOCAL_FILE_ALLOWED_DIRECTORIES": "/Users/username/Documents,/Users/username/Downloads"
      }
    }
  }
}
```

## 使用方法

セットアップ後、会話でこれらの機能を直接使用：

### 📄 読み取りとAI対応Markdownへの変換

任意のファイルをAI最適化されたMarkdown形式に変換：

```
/Users/username/Documents/report.pdf の内容を読み取り
→ テーブル、見出し、構造を持つクリーンなMarkdownに変換

/Users/username/data.xlsx を解析してデータ構造を表示  
→ スプレッドシートデータをMarkdownテーブルとして抽出

/Users/username/presentation.pptx からテキストを抽出
→ スライドを構造化されたMarkdownセクションに整理
```

### 🔄 Markdownファイルとして保存

ドキュメントをAI対応Markdownファイルに変換・保存：

```
/Users/username/contract.pdf をMarkdown形式に変換
→ 構造化されたコンテンツでcontract.pdf.mdを作成

/Users/username/analysis.xlsx を /Users/username/output/ にMarkdownとして保存
→ フォーマットされたテーブルとデータをMarkdownとして保存
```

## 設定

### 基本設定 (.env)

```bash
# ファイルアクセス制御（必須）
LOCAL_FILE_ALLOWED_DIRECTORIES=/Users/username/Documents,/Users/username/Downloads

# パフォーマンス最適化
TOTAL_CACHE_SIZE_MB=500          # 統一キャッシュ制限
CACHE_EXPIRE_DAYS=30             # キャッシュ保持期間
FILE_READER_MAX_FILE_SIZE_MB=20  # ファイルサイズ制限

# ログ記録
LOG_LEVEL=INFO
```

### オプションOCR設定

画像テキスト認識用：

```bash
# OCR用ビジョンモデル
LLM_VISION_BASE_URL=https://api.openai.com/v1
LLM_VISION_API_KEY=sk-your-api-key-here
LLM_VISION_MODEL=gpt-4o  # またはqwen-vl-plus
```

## 環境変数

| 変数 | 必須 | デフォルト | 説明 |
|----------|----------|---------|-------------|
| `LOCAL_FILE_ALLOWED_DIRECTORIES` | ✅ | `current_dir` | カンマ区切りの許可ディレクトリ |
| `TOTAL_CACHE_SIZE_MB` | ❌ | `500` | 統一キャッシュサイズ制限 |
| `FILE_READER_MAX_FILE_SIZE_MB` | ❌ | `20` | 最大ファイルサイズ |
| `LOG_LEVEL` | ❌ | `INFO` | ログレベル |
| `LLM_VISION_API_KEY` | ❌ | - | OCRビジョンモデルAPIキー |

## MCPツール

### `read_local_file`

ローカルファイルからコンテンツを抽出し、AI最適化されたMarkdownとして返す。

| パラメータ | 型 | 説明 |
|-----------|------|-------------|
| `file_path` | string | ファイルの絶対パス |
| `max_size` | number | ファイルサイズ制限（MB）（オプション） |

### `convert_local_file`

ファイルをAI対応Markdownに変換し、ファイルシステムに保存。

| パラメータ | 型 | 説明 |
|-----------|------|-------------|
| `file_path` | string | 入力ファイルの絶対パス |
| `output_path` | string | 出力パス（オプション、デフォルトは入力+.md） |
| `max_size` | number | ファイルサイズ制限（MB）（オプション） |
| `overwrite` | boolean | 既存ファイルを上書き（デフォルト：false） |

## サポートされるファイル形式

### ドキュメント形式
- **PDF**: `.pdf`
- **Microsoft Office**: `.doc`, `.docx`, `.ppt`, `.pptx`, `.xls`, `.xlsx`
- **OpenDocument**: `.odt`, `.ods`, `.odp`
- **テキスト**: `.txt`, `.md`, `.rtf`, `.csv`, `.json`, `.xml`

### 画像形式（OCR対応）
- **一般的**: `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.tiff`
- **高度**: `.webp`, `.svg`

### アーカイブ形式
- **圧縮**: `.zip`, `.tar`, `.tar.gz`, `.7z`
- **Office**: `.docx`, `.xlsx`, `.pptx`（内部的にzipベース）

### 特殊形式
- **電子書籍**: `.epub`
- **データ**: `.csv`, `.tsv`, `.json`

## アーキテクチャ

### コアコンポーネント

- **FileReader** (`src/file_reader/core.py`): ファイルコンテンツ抽出のメインオーケストレーター
- **MCP Server** (`src/mcp_server.py`): MCPツールを提供するFastMCPベースサーバー
- **Parser System** (`src/file_reader/parsers/`): 異なるファイルタイプ用の専門パーサー
- **Cache Manager** (`src/file_reader/cache_manager.py`): 統一キャッシュシステム
- **Storage Layer** (`src/file_reader/storage/`): 安全なローカルファイルアクセス

### パフォーマンス最適化

1. **統一キャッシュ**: 複数ではなく単一のキャッシュインスタンス（約6GBから500MBデフォルトに削減）
2. **遅延読み込み**: 起動時ではなく必要時にパーサーを読み込み
3. **依存関係最適化**: 高度機能用のオプション依存関係
4. **リソース制限**: 設定可能なメモリとファイルサイズ制限

## 開発

### 開発環境セットアップ

```bash
git clone https://github.com/freefish1218/mcp-local-reader.git
cd mcp-local-reader
uv sync
source .venv/bin/activate  # Unix/macOSの場合
```

### テスト実行

```bash
# すべてのテストを実行
uv run python tests/run_tests.py

# 特定のテストカテゴリ
uv run python tests/run_tests.py --models     # データモデル
uv run python tests/run_tests.py --parsers    # ファイルパーサー
uv run python tests/run_tests.py --core       # コア機能
uv run python tests/run_tests.py --server     # MCPサーバー

# カバレッジ付き
uv run python tests/run_tests.py -c

# 代替pytest使用法
PYTHONPATH=src uv run pytest tests/ -v
```

### 新しいパーサーの追加

1. `src/file_reader/parsers/`でパーサーを作成
2. `BaseParser`から継承
3. `parser_loader.py`で登録
4. `tests/test_parsers.py`でテストを追加

詳細な開発ガイドについては [CONTRIBUTING.md](CONTRIBUTING.md) を参照してください。

## パフォーマンス特性

- **スマートキャッシュ**: 再変換なしで以前に処理されたファイルへの即座のアクセス
- **効率的なメモリ使用**: 6GB+から500MBデフォルトキャッシュサイズに最適化
- **高速起動**: オンデマンドコンポーネント読み込みで80%高速化
- **並列処理**: 複数のドキュメント変換の同時処理

## システム要件

- **Python**: 3.11+
- **OS**: macOS、Linux、Windows
- **メモリ**: 大きなファイル用に2GB+推奨
- **オプション**: LibreOffice（レガシーOfficeファイル）、Pandoc（特殊変換）

## FAQ

**Q: ファイルが正しく読み取れない？**  
A: `LOCAL_FILE_ALLOWED_DIRECTORIES`にファイルのディレクトリが含まれていることを確認してください。

**Q: 画像のOCRが動作しない？**  
A: 有効なビジョンモデルAPIキー（OpenAI GPT-4oまたは互換）で`LLM_VISION_API_KEY`を設定してください。

**Q: 処理速度を向上させたい？**  
A: スマートキャッシュが処理済みファイルを自動的に記憶します。すべてのファイルの新鮮な処理が必要な場合は、キャッシュディレクトリをクリアしてください。

**Q: レガシーOfficeファイル（.doc/.ppt）が失敗する？**  
A: LibreOfficeをインストールしてください：`brew install --cask libreoffice`（macOS）またはOSの同等コマンド。

**Q: どのファイル形式がサポートされていますか？**  
A: PDF、Word、Excel、PowerPoint、OpenDocument、画像（OCR付き）、アーカイブ、テキストファイルなど。

## 貢献

貢献を歓迎します！このプロジェクトへの貢献方法については [CONTRIBUTING.md](CONTRIBUTING.md) を参照してください。

## ライセンス

このプロジェクトはMITライセンスの下でライセンスされています - 詳細については [LICENSE](LICENSE) ファイルを参照してください。

## リンク

- **課題**: [課題を報告](https://github.com/freefish1218/mcp-local-reader/issues)
- **ドキュメント**: [CLAUDE.md](CLAUDE.md) 詳細な開発ガイド
- **モデルコンテキストプロトコル**: [公式MCPドキュメント](https://modelcontextprotocol.io/)

## 謝辞

- [FastMCP](https://github.com/jlowin/fastmcp)で構築
- PDF解析は[PyMuPDF4LLM](https://github.com/pymupdf/PyMuPDF4LLM)によって提供
- [DiskCache](https://github.com/grantjenks/python-diskcache)を使用したキャッシュシステム