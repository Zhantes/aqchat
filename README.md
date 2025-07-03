# aqchat

Copyright (C) 2025 Jacob Farnsworth

<img src="https://github.com/JFarAur/aqchat/raw/main/docs/img001.png" width="720" alt="aqchat interface" />

aqchat is an LLM-powered chat bot that supports retrieval-augmented question-answering over a Git repository. All you have to do is specify a repository address, and optionally, your Github credentials (if your repository is private), then you can ask aqchat questions about your codebase such as:

* Where is `someFunction` or `SomeClass` used?
* Are there any problems or bugs in `someFile.py`?
* Suggest improvements that can be made in the projects config files.
* How do the unit tests look for `someFunction`? Does the coverage look good?

aqchat is able to answer these questions and more.

Due to the way the RAG system works, aqchat is able to have a functioning "memory" even with very large codebases, and is not quite as limited by the context length of the LLM.

The "memory" of aqchat is accomplished using a vector embedding database. On first load, your codebase is divided into chunks. The chunks are then converted into vectors in an embedding space and indexed.

When you ask a question, the vector database is used to query for chunks which have the closest semantic resemblance to your message, and then these chunks are inserted as additional context for the LLM. To put it simply, an advanced search engine is used to automatically feed the LLM with additional context from your codebase which is likely to help it answer your question.

**Limitations:**

* aqchat does not save chat history. If you want to save anything from your chats permanently, you need to download it yourself (use Print to PDF).
* aqchat is intended to be used mainly with Python-focused codebases. Support may be expanded to other types of projects in the future.
* aqchat only supports Ollama. Proprietary APIs such as OpenAI and Anthropic are currently not supported.

WARNING: aqchat is *not* intended to be deployed as a public-facing app. Settings (including Github username and PAT) are saved globally, *across any and all users*. To avoid leaking your PAT, it is **strongly** recommended to do the following:

* Deploy aqchat **only** on your local machine or on a private network.
* Configure a secure PIN passcode.
* Configure HTTPS.

## Setup

It is easiest to deploy aqchat using Docker. Before deploying the app, you must perform several setup steps.

### dotenv

In the root directory of the project, create a `.env` file using the following template:

```
PROXY_HOST=127.0.0.1
PROXY_PORT=8502
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:32B
ANONYMIZED_TELEMETRY=False
```

* `PROXY_HOST` and `PROXY_PORT` will force Docker to bind the proxy server on a specific address. It is highly recommended to keep these settings as-is (if you intend to use aqchat only on your local machine) or change to an IP visible only on a private network (if you intend to work with the same repo with others on a private network).
* Change `OLLAMA_URL` and `OLLAMA_MODEL` according to your Ollama server details.
* `ANONYMIZED_TELEMETRY=False` disables Chroma's telemetry feature.

### Passcode PIN

Next, you should set up a PIN passcode for the app. To do this, create a file `.passcode_pin` in the root directory. In this file, write a PIN code of your choice. The PIN code will be used to authorize each session in aqchat. For example, you can save a passcode such as:

```
84283
```

If you fail to configure a PIN passcode in this fashion, aqchat will default to a PIN of `123`. When the insecure default PIN is used, aqchat will display a warning in the terminal.

### HTTPS

If you intend to deploy the app on a private network, it is **highly recommended** to use HTTPS. aqchat by default is configured with HTTPS enabled, but you need to add your certificates.

* Place your SSL certificates in the `certs/` folder.
* Adjust `proxy/default.conf` as necessary and ensure settings are correct and filenames match.

If you really would like to use HTTP instead, then you can use the provided `default_http.conf` instead. However, this is strongly discouraged for security reasons.

### Deployment

After performing setup steps, the app can be deployed.

Simply deploy via docker compose:

```
docker compose up -d
```

Now aqchat is running on port 8502 (unless you specified a custom port in the dotenv).

### Usage Notes

* aqchat will pull from the main branch of the repository every time the Chat page is visited. If you pushed changes to your repo and you wish to sync them with aqchat, simply refresh the page.
* The internal embedding vector database is not rebuilt from the entire repo on every pull, rather it references the diff since last pull and updates the database only with files added, modified and removed. If there are issues with changes not being visible to aqchat, you can try wiping the vector database and forcing it to regenerate. Unfortunately there is no clean way to do this from within aqchat itself (I blame this on Chroma, which for some reason has very poor support for closing an active session). To wipe the database, shut down the Docker container group and then delete the `frontend_data` volume. Note that this will also delete app configuration and you will need to re-input your Github repository and credentials next time you use aqchat.

## Acknowledgements

aqchat is built using:

* [Langchain](https://python.langchain.com/docs/introduction/) for LLM pipeline
* [Chroma](https://docs.trychroma.com/docs/overview/introduction) for document storage and embedding vector database
* [streamlit](https://docs.streamlit.io/) for UI

## License

aqchat is licensed under the terms of the GNU General Public License, version 3. See `LICENSE` for the full license text.