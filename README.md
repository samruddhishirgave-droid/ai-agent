# LangChain Tool-Using Agent

An agent built with LangChain `create_agent` and Gemini that decides when to use tools.

## Tools
- calculator: exact arithmetic (safe parser, no eval)
- web_search: Tavily / DuckDuckGo / Wikipedia fallback

## How it works
(2-3 sentences: the model reads tool descriptions, decides to call a tool, gets the result, repeats until it can answer.)

## Setup
pip install -r requirements.txt, copy .env.example to .env, add GEMINI_API_KEY (and optionally TAVILY_API_KEY), then:
python agent.py "your question"
python demo.py

## Example runs
# Example runs

Raw logs from `demo.py` (unedited).

## 1. No tool needed

```
QUESTION: What is an API? Answer in one sentence.
(no tools were used for this question)
FINAL ANSWER: An API (Application Programming Interface) is a set of rules and protocols that allows different software applications to communicate and exchange data with each other.
```

## 2. Calculator tool

```
QUESTION: What is 48,372 x 9,184 + 2^20?
TOOL CALL #1: calculator({'expression': '48372 * 9184 + 2**20'})
TOOL RESULT (calculator): 445297024
FINAL ANSWER: The exact result of the expression $48,372 \times 9,184 + 2^{20}$ is **445,297,024**.
```

## 3. Search tool

```
QUESTION: What is the latest stable version of Python?
TOOL CALL #1: web_search({'query': 'latest stable version of python'})
TOOL RESULT (web_search): (search source: Tavily)

[1] Latest Python Version (2025) – What's New in Python 3.14?
The latest major version, Python 3.14 was officially released on October 7, 2025.

Let’s explore the key features of Python’s current version, how to download and install it, and what this release means for developers.

## Get premium VPS hosting

High-performance VPS hosting that delivers unrivaled power

Explore VPS hosting

## What’s the latest Python version?

The latest stable version of Pyth
URL: https://www.liquidweb.com/blog/latest-python-version

[2] History of Python - Wikipedia
As of October 2026(...
TOOL CALL #2: web_search({'query': 'site:python.org downloads latest release'})
TOOL RESULT (web_search): (search source: Tavily)

[1] Download Python | Python.org
News
       Python News
       PSF Newsletter
       PSF News
       PyCon US News
       Python Insider
       News from the Community

   Events
       Python Events
       User Group Events
       Python Events Archive
       User Group Events Archive
       Submit an Event

# Download the latest version for Android

# Download the latest source release

Download Python 3.15.2

# Download the l
URL: https://www.python.org/downloads

[2] Downloading python question - Python Help - Discussions on Python.org
When you click on “Windows” ...
FINAL ANSWER: The latest stable version of Python is **Python 3.15.2**, as listed on the official Python.org downloads page.
```

## 4. Multi-step (search, then calculate)

```
QUESTION: Find the height of Mount Everest and of the Burj Khalifa in metres, then calculate how many times taller Everest is, rounded to 2 decimals.
TOOL CALL #1: web_search({'queries': ['height of Mount Everest in metres', 'height of Burj Khalifa in metres']})
TOOL RESULT (web_search): Error invoking tool 'web_search' with kwargs {'queries': ['height of Mount Everest in metres', 'height of Burj Khalifa in metres']} with error:
 query: Field required
 Please fix the error and try again.
TOOL CALL #2: web_search({'query': 'height of Mount Everest in metres'})
TOOL RESULT (web_search): (search source: Tavily)

[1] Mount Everest
On 9 October 2005, after several months of measurement and calculation, the Chinese Academy of Sciences and State Bureau of Surveying and Mapping announced the height of Everest as 8,844.43 m (29,017.16 ft) with accuracy of ±0.21 m (8.3 in), claiming it was the most accurate and precise measurement to date.( This height is based on the highest point of rock and not the snow and ice covering it. Th
URL: https://en.wikipedia.org/wiki/Mount_Everest

[2] Mount Everest | Height, Map, Deaths, Facts, & Climbers
a “rock height” of 29,017.12 feet (8,844.43 met...
TOOL CALL #3: web_search({'query': 'height of Burj Khalifa in metres'})
TOOL RESULT (web_search): (search source: Tavily)

[1] Burj Khalifa - Wikipedia
is a megatall skyscraper in Dubai, United Arab Emirates. Designed by Skidmore, Owings & Merrill "SOM (architectural firm)"), it is the world's tallest structure, with a total height of 829.8 m (2,722 ft, or just over half a mile) and a roof height (excluding the antenna, but including a 242.6 m spire) of 828 m (2,717 ft). It has been the tallest building in the world since its complete inauguratio
URL: https://en.wikipedia.org/wiki/Burj_Khalifa

[2] Burj Khalifa: Height, Floors, Cost | Skyscraper Day
The Burj Khalifa is 828 m (2,717 ft) tal...
THOUGHT: I need to calculate the ratio between the height of Mount Everest and the Burj Khalifa.
TOOL CALL #4: calculator({'expression': '8848.86 / 828'})
TOOL RESULT (calculator): 10.6870289855
FINAL ANSWER: * Height of Mount Everest: 8,848.86 metres (jointly declared by Nepal and China in 2020)
* Height of the Burj Khalifa: 828 metres (architectural height)

Mount Everest is **10.69** times taller than the Burj Khalifa. 

*(Figures obtained from BBC News and Wikipedia).*
```

## 5. Tool failure (division by zero)

```
QUESTION: Use the calculator to compute 100 / (5 - 5) and explain the result.
TOOL CALL #1: calculator({'expression': '100 / (5 - 5)'})
TOOL RESULT (calculator): Error: division by zero.
FINAL ANSWER: The calculator returns an error because `5 - 5` evaluates to `0`, resulting in a division by zero (`100 / 0`). In mathematics, division by zero is undefined because no number can be multiplied by zero to yield 100.
```


## Observations

- **It used tools only when needed.** The question "What is an API?" was answered directly with no tool calls (the log says "no tools were used"). The arithmetic question triggered the calculator, and the Python version question triggered web search.
- **The calculator gave exact results.** For `48,372 x 9,184 + 2^20` the model rewrote the expression as `48372 * 9184 + 2**20` and the tool returned 445297024, which the final answer repeated.
- **The agent cross-checked a weak search result.** For the latest Python version, the first search returned an article about Python 3.14 from 2025, which looked outdated. The agent ran a second, more targeted query (`site:python.org downloads latest release`) and answered with Python 3.15.2 from the official downloads page.
- **Multi-step task worked, with a recoverable tool error.** For the Everest/Burj Khalifa question the agent made four tool calls: three searches and one calculation (8848.86 / 828 = 10.687, reported as 10.69). Its first search call used a `queries` list, which my tool does not accept. The framework returned a validation error ("query: Field required") as a tool message instead of crashing, and the agent fixed its call and searched each topic separately.
- **Tool failure was handled without a crash.** For `100 / (5 - 5)` the calculator returned "Error: division by zero." and the agent explained why the result is undefined.
- **Reasoning is visible, but only partly.** The log shows every tool call, its arguments and its result. A "THOUGHT" line appeared only once (before the calculation in the multi-step run). In the other runs the model called tools without writing a reason first, even though the system prompt asks for one, so the "why" has to be inferred from the queries it chose.
- **Formatting quirk:** in the calculator run, the final answer contained LaTeX markup (`$48,372 \times 9,184 + 2^{20}$`), which reads badly in a plain terminal.

## Limitations

- **Small test set.** I ran 5 questions, once each. LLM behaviour varies between runs, so these logs show that the pipeline works, not how reliable it is.
- **Search quality limits answer quality.** The first Python search returned an outdated article. The agent noticed this time, but nothing in my code forces it to check source dates. Search snippets are also cut short (400 characters per result from Tavily, and the log prints only the first 600 characters of each tool result), so a fact can be missing from what the model sees or from what the log shows.
- **Sources are not verified.** In the multi-step run the sources gave different Everest heights (8,844.43 m in one result, 8,848.86 m in the final answer). The model picked one and cited sources, but my code does not check that a cited source really contains the stated figure.
- **Search providers differ in reliability.** DuckDuckGo (via `ddgs`) returned no results on my network, so I used Tavily (free tier, limited credits). The fallback, Wikipedia, does not provide real-time news.
- **Time-sensitive answers expire.** The "latest Python version" answer is correct only as of the search run and can become outdated.
- **Only two tools.** The calculator is arithmetic only (no units, no variables, exponent limit of 1000), and there is no code-execution tool.
- **No memory between questions.** Each question is a separate agent run, so the agent cannot refer to an earlier question. A step limit (15) stops runaway loops, and API rate limits (Gemini, Tavily) are handled only by returning an error message.

## Limitations
- **Small test set.** I ran 5 questions, once each. LLM behaviour varies between runs, so these logs show that the pipeline works, not how reliable it is.
- **Search quality limits answer quality.** The first Python search returned an outdated article. The agent noticed this time, but nothing in my code forces it to check source dates. Search snippets are also cut short (400 characters per result from Tavily, and the log prints only the first 600 characters of each tool result), so a fact can be missing from what the model sees or from what the log shows.
- **Sources are not verified.** In the multi-step run the sources gave different Everest heights (8,844.43 m in one result, 8,848.86 m in the final answer). The model picked one and cited sources, but my code does not check that a cited source really contains the stated figure.
- **Search providers differ in reliability.** DuckDuckGo (via `ddgs`) returned no results on my network, so I used Tavily (free tier, limited credits). The fallback, Wikipedia, does not provide real-time news.
- **Time-sensitive answers expire.** The "latest Python version" answer is correct only as of the search run and can become outdated.
- **Only two tools.** The calculator is arithmetic only (no units, no variables, exponent limit of 1000), and there is no code-execution tool.
- **No memory between questions.** Each question is a separate agent run, so the agent cannot refer to an earlier question. A step limit (15) stops runaway loops, and API rate limits (Gemini, Tavily) are handled only by returning an error message.