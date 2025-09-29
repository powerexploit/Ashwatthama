<h1 align="center">
  <br>
  <a href="https://github.com/powerexploit/Ashwatthama"><img src="/static/ashwatthama.png" alt="Ashwatthama logo"></a>
</h1>

<h4 align="center">Most advanced tech and service detection suite.</h4>

Ashwatthama is a command-line tool designed for service detection and version identification across multiple URLs. It leverages custom signatures to detect technologies and their versions from various sources like headers, content and cookies.

## Features
- **Technology Detection**: Identify various web technologies based on custom signatures
- **Version Detection**: Detect the version of the identified technologies
- **Multi-URL Support**: Process a single URL or a list of URLs
- **Fast Processing**: Utilizes ThreadPoolExecutor for concurrent requests, speeding up the detection process
- **Custom Signatures**: Easily extend the tool's detection capabilities via custom signatures
- **Fallback Regex Engine**: Works without external dependencies like ripgrep
- **Progress Indicators**: Real-time progress tracking for batch operations
- **Multiple Output Formats**: JSON output with optional file saving
- **Comprehensive Error Handling**: Robust error handling and logging
- **Configuration Support**: YAML-based configuration system
- **Memory Efficient**: Optimized memory usage with caching

## Installation

1. Clone the repository:
```bash
git clone https://github.com/powerexploit/Ashwatthama
cd Ashwatthama
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

3. (Optional) Download and install 'ripgrep' from [GitHub Releases](https://github.com/BurntSushi/ripgrep/releases) for enhanced performance with large content

## Usage

### Basic Usage
```bash
# Scan a single URL
python3 src/cli.py --url https://example.com

# Scan multiple URLs from a file
python3 src/cli.py --url-list urls.txt

# Save results to a file
python3 src/cli.py --url https://example.com --output results.json

# Scan with custom thread count
python3 src/cli.py --url https://example.com --threads 5

# Disable colored output
python3 src/cli.py --url https://example.com --no-color
```

### Advanced Usage
```bash
# Verbose output with custom timeout
python3 src/cli.py --url https://example.com --verbose --timeout 30

# Batch processing with output file
python3 src/cli.py --url-list urls.txt --output batch_results.json --threads 8
```

## Configuration

Ashwatthama supports configuration via `config.yaml`:

```yaml
# Request settings
request:
  timeout: 15
  max_retries: 3
  user_agent_rotation: true
  follow_redirects: true
  verify_ssl: false

# Threading settings
threading:
  max_workers: 10
  thread_timeout: 30

# Output settings
output:
  default_format: "json"
  colorize: true
  verbose: false
  save_logs: true
```

## Custom Signatures

One of the powerful features of Ashwatthama is its ability to be extended through custom signatures. Researchers can add their own signatures to detect new technologies or refine existing detections.

### Signature Template Format
A signature is defined as a JSON object that contains the rules for detecting a specific technology and its version:

```json
{
    "techName": "TechnologyName",
    "discoveryRules": [
        {
            "type": "header",
            "path": "/",
            "techRegex": "TechnologyRegex",
            "versionRegex": "VersionRegex"
        },
        {
            "type": "content",
            "path": "/",
            "techRegex": "TechnologyRegex",
            "versionRegex": "VersionRegex"
        }
    ]
}
```

- **techName**: The name of the technology that the signature is designed to detect
- **discoveryRules**: A list of rules that define where and how to look for the technology

Each discovery rule contains the following fields:
- **path**: The specific path on the web application to check
- **techRegex**: A regular expression used to identify the technology within the specified source
- **versionRegex**: A regular expression used to extract the version of the technology from the source
- **type**: The type of source to search. Can be `content` (HTML content), `header` (HTTP header), or `cookies`

### Adding Your Custom Signatures
To add your custom signatures:
1. Create a new JSON file in the `signatures/` directory
2. Add your custom signatures in the format described above
3. Run the tool as usual. Your new signatures will be automatically loaded and used during detection

## Improvements in v1.1

- **Fixed Import Issues**: Resolved all module dependency problems
- **Enhanced Error Handling**: Comprehensive error handling throughout the codebase
- **Memory Management**: Fixed temporary file cleanup and memory leaks
- **Fallback Regex Engine**: Works without ripgrep dependency
- **Progress Indicators**: Real-time progress tracking for batch operations
- **Output Formatting**: Improved JSON output with colorization
- **Configuration System**: YAML-based configuration support
- **Input Validation**: URL validation and sanitization
- **Performance Optimization**: Reduced thread count and improved efficiency
- **Better Logging**: Enhanced logging with proper levels and formatting


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
