# QAG Agent Demo

This demo serves to modernize the Query Augmented Generation (QAG) framework using contemporary agentic concepts. The first iteration of QAG relied on a custom LLM to infer the intent of user queries. After categorizing the intent, a secondary model and static retrieval system were used to gather the entities required to query the GDC API. Manual routing and orchestration using the intent and entities was done to construct and execute the GDC API queries. Finally, the resulting information was parsed by a tertiary LLM for final return to the user. These steps are fragile and do not scale well: the custom model to infer user intent was trained on poorly generated, templated synthetic queries for a small subset of tasks; additional tasks require manual curation of entity maps as well as custom router logic; and tasks are hard-coded and result in code duplication without sufficient modularization.

Modern agentic LLMs with well-documented MCP tools are sufficiently powerful to simplify all of these steps. Given MCP tool descriptions, an LLM agent can determine which tools are most appropriate for the given user query. Additionally, the agent can dynamically extract the entitities from the user's query and correctly prepare them in the input format required by the tools. When multiple steps of API queries are potentially necessary, the agent can dynamically plan and execute multi-round tool calls to accomplish a complex task. Yet, for simpler tasks, the modular tool design allows for direct reuse without custom logic or implementation.

## Example queries

For this demo, we test 2 example queries from the QAG paper:
* Simple Somatic Mutations:
    ```
    what is the co-occurrence frequency of IDH1 R132H and TP53 R273C simple somatic mutations in the low grade glioma project TCGA-LGG in the genomic data commons?
    ```
    * <details>
      <summary>Expand for Claude Desktop answer</summary>

      ![Claude Desktop response to SSM query](figs/claude_desktop_ssm.png)

      </details>
    * <details>
      <summary>Expand for locally-served <code>gpt-oss-120b</code> agent answer</summary>

        ```
        ================================ System Message ================================

        You are a helpful bioinformatics assistant. Use the provided tools to answer genomics questions. You may need to perform multiple tool calls to arrive at the final answer.

        ================================ Human Message =================================

        what is the co-occurrence frequency of IDH1 R132H and TP53 R273C simple somatic mutations in the low grade glioma project TCGA-LGG in the genomic data commons?

        ================================== Ai Message ==================================
        Tool Calls:
        get_simple_somatic_mutation_ids (f579677d-93ff-46c2-9b3a-5a54ee9be51e)
        Call ID: f579677d-93ff-46c2-9b3a-5a54ee9be51e
        Args:
            aa_change: R132H
            gene: IDH1

        ================================= Tool Message =================================
        Name: get_simple_somatic_mutation_ids

        [{'type': 'text', 'text': 'fa9713e8-ce92-5413-aacc-ed3d95ab7906', 'id': 'lc_43a4c216-d3bf-4ce5-b999-ef31d3597ed5'}]

        ================================== Ai Message ==================================
        Tool Calls:
        get_simple_somatic_mutation_ids (30ed74b6-1b38-465e-98e6-7f6b425c7b7c)
        Call ID: 30ed74b6-1b38-465e-98e6-7f6b425c7b7c
        Args:
            aa_change: R273C
            gene: TP53

        ================================= Tool Message =================================
        Name: get_simple_somatic_mutation_ids

        [{'type': 'text', 'text': '477e2125-974b-5af0-a876-25596d99ddbf', 'id': 'lc_08b3b5ec-d748-43f4-b522-1caa65ac79c8'}]

        ================================== Ai Message ==================================
        Tool Calls:
        get_simple_somatic_mutation_occurrences (1398b1e2-eb48-48c3-9faf-287ccfda4179)
        Call ID: 1398b1e2-eb48-48c3-9faf-287ccfda4179
        Args:
            ssm_ids: ['fa9713e8-ce92-5413-aacc-ed3d95ab7906']

        ================================= Tool Message =================================
        Name: get_simple_somatic_mutation_occurrences

        [{'type': 'text', 'text': 'fef22b72-3a6c-40f9-bf3e-d1b2a05d93c9', 'id': 'lc_40158b64-1012-46e2-a39f-51a952bc3099'}]

        ================================== Ai Message ==================================
        Tool Calls:
        get_simple_somatic_mutation_occurrences (18d562fd-1f89-4ae5-950f-89b4b6a508c5)
        Call ID: 18d562fd-1f89-4ae5-950f-89b4b6a508c5
        Args:
            ssm_ids: ['...']

        ================================= Tool Message =================================
        Name: get_simple_somatic_mutation_occurrences

        [{'type': 'text', 'text': '21702c8a-b30a-44c3-8ec3-d5fbedb894bc', 'id': 'lc_73d111cc-6a9f-43e2-ba10-f06593e723bb'}]

        ================================== Ai Message ==================================
        Tool Calls:
        get_simple_somatic_mutation_occurrences (d55b8425-ae6b-4019-a193-8865bd00eb1e)
        Call ID: d55b8425-ae6b-4019-a193-8865bd00eb1e
        Args:
            ssm_ids: ['477e2125-974b-5af0-a876-25596d99ddbf']

        ================================= Tool Message =================================
        Name: get_simple_somatic_mutation_occurrences

        [{'type': 'text', 'text': '13bb350d-e471-4c28-ac39-4aeeee9b78c0', 'id': 'lc_efc04eea-d270-4548-9c74-fab16cb6a57f'}]

        ================================== Ai Message ==================================
        Tool Calls:
        get_cases_by_project (4610f44a-09b4-4efc-8ac7-f2457e24bab8)
        Call ID: 4610f44a-09b4-4efc-8ac7-f2457e24bab8
        Args:
            project: TCGA-LGG

        ================================= Tool Message =================================
        Name: get_cases_by_project

        [{'type': 'text', 'text': '8e5896ea-ab74-4fbc-b6cb-9e191b4484b8', 'id': 'lc_d467c13e-0f89-44df-982b-b3dcd42472a9'}]

        ================================== Ai Message ==================================
        Tool Calls:
        get_case_cooccurrence_frequency_by_project (ef82a7f2-7f8b-4ad1-9a78-0415791f173f)
        Call ID: ef82a7f2-7f8b-4ad1-9a78-0415791f173f
        Args:
            cases_A: fef22b72-3a6c-40f9-bf3e-d1b2a05d93c9
            cases_B: 13bb350d-e471-4c28-ac39-4aeeee9b78c0
            cases_project: 8e5896ea-ab74-4fbc-b6cb-9e191b4484b8

        ================================= Tool Message =================================
        Name: get_case_cooccurrence_frequency_by_project

        [{'type': 'text', 'text': '{\n  "cooccurrence_count": 36,\n  "total_project_cases": 516,\n  "cooccurrence_frequency": 0.06976744186046512\n}', 'id': 'lc_95d9b502-7c75-4776-b9ef-e9823217fe6a'}]

        ================================== Ai Message ==================================

        The co‑occurrence frequency of the **IDH1 R132H** and **TP53 R273C** simple somatic mutations within the **TCGA‑LGG (Low‑Grade Glioma)** project is:

        **≈ 0.07 (7 %)**

        - **Co‑occurring cases:** 36
        - **Total TCGA‑LGG cases examined:** 516

        Thus, about 7 % of low‑grade glioma cases in TCGA harbor both the IDH1 R132H and TP53 R273C mutations.
        ```

      </details>
* Copy Number Variants:
    ```
    what is the co-occurrence frequency of somatic homozygous deletions in CDKN2A and CDKN2B in the mesothelioma project TCGA-MESO in the genomic data commons?
    ```
    * <details>
      <summary>Expand for Claude Desktop answer</summary>

      ![Claude Desktop response to CNV query](figs/claude_desktop_cnv.png)

      </details>
    * <details>
      <summary>Expand for locally-served <code>gpt-oss-120b</code> agent answer</summary>

        ```
        ================================ System Message ================================

        You are a helpful bioinformatics assistant. Use the provided tools to answer genomics questions. You may need to perform multiple tool calls to arrive at the final answer.

        ================================ Human Message =================================

        what is the co-occurrence frequency of somatic homozygous deletions in CDKN2A and CDKN2B in the mesothelioma project TCGA-MESO in the genomic data commons?

        ================================== Ai Message ==================================
        Tool Calls:
        get_copy_number_variant_occurrences (3f3be928-4927-4761-9757-d50422b784a3)
        Call ID: 3f3be928-4927-4761-9757-d50422b784a3
        Args:
            cnv_change: homozygous deletion
            gene: CDKN2A

        ================================= Tool Message =================================
        Name: get_copy_number_variant_occurrences

        [{'type': 'text', 'text': 'b61749de-cbd9-41af-9bbf-747f50188c61', 'id': 'lc_b3dc193b-6bcb-4bc2-b316-5f21ad5d1c98'}]

        ================================== Ai Message ==================================
        Tool Calls:
        get_copy_number_variant_occurrences (16ec47a7-8884-453e-9b1b-32ca25596df6)
        Call ID: 16ec47a7-8884-453e-9b1b-32ca25596df6
        Args:
            cnv_change: homozygous deletion
            gene: CDKN2B

        ================================= Tool Message =================================
        Name: get_copy_number_variant_occurrences

        [{'type': 'text', 'text': 'a5360f7f-55d9-4a90-b5c4-9fa7391d0ba0', 'id': 'lc_dc076ada-0068-4e49-8745-edf56dc0c7fd'}]

        ================================== Ai Message ==================================
        Tool Calls:
        get_cases_by_project (7ad58c8a-5e4c-43bd-b132-f7bb3cc28aef)
        Call ID: 7ad58c8a-5e4c-43bd-b132-f7bb3cc28aef
        Args:
            project: TCGA-MESO

        ================================= Tool Message =================================
        Name: get_cases_by_project

        [{'type': 'text', 'text': '1c679110-3811-4a67-83f9-a02707561d81', 'id': 'lc_49c1cab6-764a-4515-a3f5-8b23e394fe09'}]

        ================================== Ai Message ==================================
        Tool Calls:
        get_case_cooccurrence_frequency_by_project (f0a05890-bfd6-4cac-a8e5-ba048cf95d54)
        Call ID: f0a05890-bfd6-4cac-a8e5-ba048cf95d54
        Args:
            cases_A: b61749de-cbd9-41af-9bbf-747f50188c61
            cases_B: a5360f7f-55d9-4a90-b5c4-9fa7391d0ba0
            cases_project: 1c679110-3811-4a67-83f9-a02707561d81

        ================================= Tool Message =================================
        Name: get_case_cooccurrence_frequency_by_project

        [{'type': 'text', 'text': '{\n  "cooccurrence_count": 39,\n  "total_project_cases": 87,\n  "cooccurrence_frequency": 0.4482758620689655\n}', 'id': 'lc_e260e742-da33-42bd-9b30-786133d69bdc'}]

        ================================== Ai Message ==================================

        The co‑occurrence frequency of **homozygous deletions** in **CDKN2A** and **CDKN2B** within the **TCGA‑MESO (mesothelioma)** project is:

        **≈ 0.45 (44.8 %)**

        This means that about 39 of the 87 mesothelioma cases in TCGA have homozygous deletions affecting both CDKN2A and CDKN2B.
        ```

      </details>

## Connect to the MCP server using Claude Desktop

At its core, this demo relies on a strong LLM and an MCP server. If you don't have access to a high-capacity GPU, you can still test out the demo by connecting the MCP server to a frontier-model provider (honestly, these resutls tend to be stronger). This section specifically details how to test out the MCP tools using Claude Desktop.
1. Download and install Claude Desktop (https://claude.com/download)
1. Download and install `uv` (https://docs.astral.sh/uv/#installation)
1. Clone this repository and setup your virtual environment:
    ```
    git clone git@github.com:StevenSong/qag-agent-demo.git
    cd qag-agent-demo
    uv venv --python 3.12.12
    uv pip install -r requirements.txt
    source .venv/bin/activate
    ```
1. Open Claude Desktop, go to Settings > Developer > Edit Config, and open the file `claude_desktop_config.json` in your favorite text editor
1. Add the following section to your JSON config file, note that you should provide absolute paths for `uv` and `qag-agent-demo`:
    ```
    "mcpServers": {
        "gdc": {
            "command": "/path/to/uv"
            "args": [
                "--directory",
                "/path/to/qag-agent-demo",
                "run",
                "server.py",
                "-t",
                "stdio"
            ]
        }
    }
    ```
1. Restart Claude Desktop (must fully close the application to reload the config)
1. Verify that the `gdc` MCP server has started by checking the enabled "Connectors" (from the main prompt UI, click the `+` sign in the lower left, Connectors submenu)
1. Try the example queries (you'll need to approve the tool usage through the UI)

## Using a locally served agent

If you have access to a high-capacity GPU (e.g. 80GB of VRAM), you can use a capable open-weight reasoning model to create an agent which queries the GDC through the MCP server. To that end, we use the following tools:
* `openai/gpt-oss-120b` as our reasoning/tool calling model
* dockerized `ollama` to serve the LLM
* `FastMCP` to define our MCP server
* `langchain` to create our agent
    * `langchain-ollama` to connect to our `ollama` instance
    * `langchain-mcp-adapters` to connect to our MCP instance

#### Setup

Clone this repo and setup your environment. We use conda below but you can alternatively use any other virtual environment manager (eg `uv`) and install directly from `requirements.txt`. If you use something other than conda, make sure to use the same python version (`3.12.12`).

```
conda create -f env.yaml
conda activate qag-agent-demo
```

#### Run Servers

Once you've setup and activated your environment, start the `ollama` and MCP servers:
```
# start the ollama server, change the GPU index as needed
docker run -d --rm --gpus='"device=0"' -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
docker exec ollama ollama run gpt-oss:120b

# start the MCP server
python server.py
```

#### Execute Queries

To execute these queries, run the agent:
```
python agent.py "<query>"
```

## Notes
* Because the entire agent orchestration is dynamic and LLM-driven, it is possible for the LLM to make mistakes. While there are observed stabilities issues with this demo (e.g. with the SSM query), these are potentially solveable using standard LLM prompting techniques (see next bullet).
* The crux of an MCP server is the quality of the tool descriptions, including the purpose of the tool and the semantics and format of the arguments. The current tool descriptions were created very quickly in a single morning. There's alot of room for improvement.
* Another observation for instability may be the model's ability to parse and pass around UUIDs. This is precisely why the demo server uses a server side cache for very long lists of case IDs that can be referenced by a single UUID, but even then, sometimes the model gets weird outputs when trying to parse/repeat UUIDs.
* This demo currently does not use structured outputs, but that should be trivial to add.

## Demo V2

In `server-v2.py`, we extend the original demo to support all queries of the GDC-QAG paper (more below). In v2, we address some of the notes and limitations mentioned above. We first improve tool architecture by focusing tool purposes and clarify tool parameter descriptions and server instructions. We additionally remove UUIDs in favor of more natural-language-style identifiers, e.g. "Cases-SSM-BRAF" for cases with SSM mutation in BRAF. In place of running the original `server.py`, use `server-v2.py` as a drop-in for enhanced capabilities.

### Generalizing to all the queries of the GDC-QAG paper
In the GDC-QAG paper, there are 6011 templated queries that are used for evaluation. These queries can be categorized and solved as follows:
* SSM and CNV by Project:
    * Example:
        > What percentage of cancers have simple somatic mutations and copy number variants in BRAF in the genomic data commons for NCI Cancer Model Development for the Human Cancer Model Initiative HCMI-CMDC project?
    * Templates (as regexes):
        ```python
        r"What percentage of cancers have simple somatic mutations and copy number variants in (.+?) in the genomic data commons for (.+?) project\?"
        r"What is the incidence of simple somatic mutations and copy number variants in (.+?) in the genomic data commons for (.+?) project \?"
        r"How common are simple somatic mutations and copy number variants in (.+?) in (.+?) project in the genomic data commons\?"
        r"What fraction of cases have simple somatic mutations and copy number variants in (.+?) in (.+?) project in the genomic data commons\?"
        r"What proportion of cancer patients exhibit simple somatic mutations and copy number variants in (.+?) in (.+?) project in the genomic data commons\?"
        r"What is the frequency of simple somatic mutations and copy number variants in (.+?) in (.+?) project in the genomic data commons\?"
        ```
    * Solve strategy:
        * Find cases C1 with SSM in gene
        * Find cases C2 with CNV in gene
        * Find cases P within project
        * Compute C12 = C1 ∩ C2
        * Compute Ret = C12 ∩ P
* SSM by Project:
    * Example:
        > How often is the BRAF V600E found in Skin Cutaneous Melanoma TCGA-SKCM project in the genomic data commons?
    * Templates (as regexes):
        ```python
        HGVS = r"[A-Z]\d+(?:[A-Z](?:fs\*\d+)?|\*)" # missense, nonsense, frameshift
        rf"How often is the (.+?) ({HGVS}?) found in (.+?) project in the genomic data commons\?"
        rf"What is the occurrence rate of (.+?) ({HGVS}?) in (.+?) project in the genomic data commons \?"
        rf"What is the rate of occurrence of (.+?) ({HGVS}?) mutation in (.+?) project in the genomic data commons\?"
        rf"How frequently are (.+?) ({HGVS}?) mutations detected in (.+?) project in the genomic data commons\?"
        rf"What is the frequency of (.+?) ({HGVS}?) in (.+?) project in the genomic data commons\?"
        ```
    * Solve strategy:
        * Find cases C with SSM in gene resulting in AA change
        * Find cases P within project
        * Compute Ret = C ∩ P
* CNV by Project:
    * Example:
        > What is the frequency of somatic JAK2 heterozygous deletion in Acute Lymphoblastic Leukemia - Phase II TARGET-ALL-P2 project in the genomic data commons?
    * Templates (as regexes):
        ```python
        r"What is the frequency of somatic (.+?) heterozygous deletion in (.+?) project in the genomic data commons\?"
        r"What is the incidence of somatic (.+?) homozygous deletion in (.+?) project in the genomic data commons\?"
        r"Can you provide the frequency of (.+?) gain in (.+?) project in the genomic data commons\?"
        r"In (.+?) project data from the genomic data commons, what is the frequency of (.+?) amplification\?"
        ```
    * Solve strategy:
        * Find cases C with CNV in gene with specific change type
        * Find cases P within project
        * Compute Ret = C ∩ P
* MSI by Project:
    * Example:
        > How common is microsatellite instability in Genomic Characterization CS-MATCH-0007 Arm S1 MATCH-S1 project cases in the genomic data commons?
    * Templates (as regexes):
        ```python
        r"How common is microsatellite instability in (.+?) project cases in the genomic data commons\?"
        r"Can you provide the prevalence of microsatellite instability in (.+?) project in the genomic data commons\?"
        r"What percentage of (.+?) project patients have microsatellite instability in the genomic data commons\?"
        r"How often is microsatellite instability observed in (.+?) project in the genomic data commons\?"
        r"In (.+?) project, what is the occurrence rate of microsatellite instability in the genomic data commons\?"
        r"What is the incidence of microsatellite instability in (.+?) project in the genomic data commons\?"
        r"What is the frequency of microsatellite instability in (.+?) project in the genomic data commons\?"
        ```
    * Solve strategy:
        * Find cases C with MSI
        * Find cases P within project
        * Compute Ret = C ∩ P
* Co-occurrence by Project:
    * Example:
        > What is the co-occurence frequency of somatic heterozygous deletions in CDKN2A and CDKN2B in the mesothelioma project TCGA-MESO in the genomic data commons?
    * Templates (as regexes):
        ```python
        r"What is the co-occurence frequency of somatic heterozygous deletions in (.+?) and (.+?) in the (.+?) in the genomic data commons\?"
        r"What is the co-occurence frequency of somatic homozygous deletions in (.+?) and (.+?) in the (.+?) in the genomic data commons\?"
        ```
    * Solve strategy:
        * Find cases C1 with condition 1
        * Find cases C2 with condition 2
        * Find cases P within project
        * Compute C12 = C1 ∩ C2
        * Compute Ret = C12 ∩ P

### Modularization and reusable components
These questions can be solved with a minimal set of tools, specifically:
1. tool to compute case intersection
1. tools to retrieve cases:
    1. by project
    1. by SSM within a gene (optionally resulting in an AA change)
    1. by CNV within a gene (optionally with a specific change type)
    1. by MSI status
