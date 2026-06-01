import os
import pandas as pd
import requests


def summarize_tnm(tnm_path):
    """
    Summarize the TNM document using OpenAI's API.

    :param tnm_path: Path to the TNM PDF document.
    :return: Path to the summary text file or error message.
    """
    # 1. Initialize ----
    glance_md_file_name = generate_glance_md_file(tnm_path)
    if not glance_md_file_name:
        print("Failed to generate glance markdown file.")
        return "Error: Glance markdown file generation failed."
    with open(glance_md_file_name) as f:
        glance_content = f.read()
    # There is a prompt management page from OpenAI, but we can't log in, so use local file temporarily.
    prompt_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "config", "tnm_prompt.md")
    with open(prompt_path) as f:
        prompt = f.read()

    # 2. Upload TNM file
    tnm_file_name = os.path.basename(tnm_path) + ".pdf"
    tnm_file_path = os.path.join(tnm_path, tnm_file_name)
    if not os.path.exists(tnm_file_path):
        print("Error: TNM PDF file does not exist.")
        return "Error: TNM PDF file does not exist."

    api_url = 'https://cygnus.telenav.com/api/ai/taskbots/call'

    try:
        data = {
            'prompt': prompt + "\n" + glance_content,
            'ai_model': 'gpt-4.1'
        }
        with open(tnm_file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(api_url, data=data, files=files)

        if response.status_code not in [200, 201]:
            print(f"API call failed with status {response.status_code}: {response.text}")
            return f"Error: API call failed - {response.text}"

        response_data = response.json()

        # 4. Get Response and Save
        if response_data.get('response'):
            tnm_number = int(os.path.basename(tnm_path).split('-')[1])
            output_file = os.path.join(tnm_path, "Glance", "Summary-{}.txt".format(tnm_number))
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(response_data['response'])
            print(f"Summary written to: {output_file}")
            return output_file
        else:
            print("No reply found in API response.")
            return "No reply found."
    except Exception as e:
        print(f"Error calling API: {str(e)}")
        return f"Error: {str(e)}"


def generate_glance_md_file(tnm_path):
    tnm_number = int(os.path.basename(tnm_path).split('-')[1])
    glance_path = os.path.join(tnm_path, "Glance")
    if not os.path.exists(glance_path):
        print("Error: Glance directory does not exist.")
        return None
    glance_md_file_name = os.path.join(glance_path, "Glance-{}.md".format(tnm_number))
    glance_excel_file_name = os.path.join(glance_path, "Glance-{}.xlsx".format(tnm_number))
    if os.path.exists(glance_md_file_name):
        print("Glance markdown file already exists, skipping generation.")
        return glance_md_file_name
    for file_name in os.listdir(glance_path):
        if file_name.endswith("Glance.xlsx"):
            origin_glance_file = os.path.join(glance_path, file_name)
            break
    else:
        print("Error: No Glance Excel file found in the directory.")
        return None
    df = pd.read_excel(origin_glance_file, header=0)
    condition = []
    for i in range(0, len(df)):
        if int(df.iloc[i, 0]) == tnm_number:
            condition.append(True)
        else:
            condition.append(False)
    df = df.loc[condition]
    df.to_excel(glance_excel_file_name, index=False)
    df = pd.read_excel(glance_excel_file_name)

    markdown_table = df.to_markdown(index=False)
    with open(glance_md_file_name, 'w') as f:
        f.write(markdown_table)

    return glance_md_file_name


if __name__ == "__main__":
    tnm_dir = "/var/www/html/docs/HERE/HERE_TNM/TNM-278"
    summarize_tnm(tnm_dir)