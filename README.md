<h1 align="center">
  <br>
  <a href="https://github.com/powerexploit/Ashwatthama"><img src="/static/ashwatthama.png" alt="Ashwatthama logo"></a>
</h1>

<h4 align="center">Most advanced tech and service detection suite.</h4>

Aswathama is a command-line tool designed for service detection and version identification across multiple URLs. It leverages custom signatures to detect technologies and their versions from various sources like headers, content and cookies.

## Features
- Technology Detection: Identify various web technologies based on custom signatures.
- Version Detection: Detect the version of the identified technologies.
- Multi-URL Support: Process a single URL or a list of URLs.
- Fast Processing: Utilizes ThreadPoolExecutor for concurrent requests, speeding up the detection process.
- Custom Signatures: Easily extend the tool's detection capabilities via custom signatures.

## Installation

1. Clone the repository:
```
git clone https://github.com/powerexploit/Ashwatthama
cd Ashwatthama
```

2. Install the required dependencies:
``` 
pip install -r requirements.txt
```

3. Download and install 'ripgrep' from [GitHub Releases](https://github.com/BurntSushi/ripgrep/releases)

## Usage
1. Aswathama supports to detect technology and version for a single URL:
```
python src/cli.py --url https://example.com
```

2. Aswathama supports to detect technologies and versions for multiple URLs provided in a file:
```
python src/cli.py --url-list example.txt
```


## Custom Signatures
One of the powerful features of Aswathama is its ability to be extended through custom signatures. Researchers can add their own signatures to detect new technologies or refine existing detections.

### Signature Template Format
A signature is defined as a JSON object that contains the rules for detecting a specific technology and its version. Here's a quick guide to the format:
```
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
- *techName:* The name of the technology that the signature is designed to detect.
- *discoveryRules:* A list of rules that define where and how to look for the technology.

Each discovery rule contains the following fields:

- *path:* The specific path on the web application to check.
- *techRegex:* A regular expression used to identify the technology within the specified source.
- *versionRegex:* A regular expression used to extract the version of the technology from the source.
- *type:* The type of source to search. Can be content (HTML content) or header (HTTP header).

### Adding Your Custom Signatures
To add your custom signatures:
- Create a new JSON file in the *signatures/* directory.
- Add your custom signatures in the format described above.
- Run the tool as usual. Your new signatures will be automatically loaded and used during detection.