from __future__ import division, print_function, unicode_literals
import os
import logging
import subprocess
import io
import xml.etree.ElementTree as ET


class TnTollCostValidator(object):
    def __init__(self, region, version, data_path):
        self.region = region
        self.version = version
        self.vendor = "{}_HERE_{}".format(self.region, self.version)
        self.workspace = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workspace")
        self.src_dir = os.path.join(self.workspace, "here_rdf")
        os.system("mkdir -p " + self.src_dir)
        self.output_dir = os.path.join(self.src_dir, "output")
        os.system("mkdir -p " + self.output_dir)
        logging.getLogger().setLevel(logging.INFO)
        self.original_dir = os.getcwd()
        os.chdir(self.workspace)
        self.data_path = data_path
        self.tollcost_xml_file = os.path.join(self.data_path, "tn_toll_cost.xml")
        self.tollcost_report_file = "/var/www/html/data/{}/check_report/tn_tollcost_report.html".format(self.vendor)
        self.s3_raw_data_path = "s3://tnavmapdata/raw_data/gemini/{}".format(self.vendor)
        self.sub_check_result = {"component": "toll_cost", "details": []}

    def __del__(self):
        os.chdir(self.original_dir)
        os.system("rm -rf " + self.workspace)

    def validate(self):
        if not os.path.exists(self.tollcost_xml_file):
            return {"status": "not ready"}, self.sub_check_result
        rdf_ready_file = "{}/.rdf_ready".format(self.s3_raw_data_path)
        if subprocess.call("aws s3 ls {}".format(rdf_ready_file), shell=True) != 0:
            return {"status": "not ready"}, self.sub_check_result
        self.download_and_merge_csv()
        return self.generate_report()

    def download_and_merge_csv(self):
        cmd = (
            'aws s3 cp {} {} --recursive --exclude "*" '
            '--include "*rdf_meta.txt.bz2" '
            '--include "*rdf_condition_toll.txt.bz2"'
        ).format(self.s3_raw_data_path, self.src_dir)
        subprocess.run(cmd, shell=True)
        cmd = '''find {} -type f -name "*.bz2" | while read -r file; do
            file_name=$(basename "$file" .txt.bz2)
            bzcat "$file" >> "{}/${{file_name}}.txt"
        done
        '''.format(self.src_dir, self.output_dir)
        subprocess.run(cmd, shell=True)
        logging.info("CSV Merged")
        cmd = '''awk -F '\\t' '$3==7 || $3==8 {{print $2}}' "{}/rdf_condition_toll.txt" | sort -u | \\
            awk -F '\\t' 'NR==FNR {{ids[$0]; next}} $1=="RDF_CONDITION_TOLL" && $2=="TOLL_SYSTEM_TYPE" && $4 in ids {{print $4,$6}}' - "{}/rdf_meta.txt" | \\
            sort -u > "{}/here_tolls.csv"
        '''.format(self.output_dir, self.output_dir, self.output_dir)
        subprocess.run(cmd, shell=True)

    def generate_report(self):
        output_csv_path = os.path.join(self.output_dir, "here_tolls.csv")
        pass_threshold = 90
        # Load XML and extract toll data
        tree = ET.parse(self.tollcost_xml_file)
        root = tree.getroot()

        name_to_tn = {}  # name -> (tn_id, [all names])
        for toll in root.findall('.//Toll'):
            tn_id = toll.get('ID')
            toll_name = toll.get('Name')

            # Collect all names (name + aliases)
            all_names = [toll_name] if toll_name else []
            aliases_elem = toll.find('Aliases')
            if aliases_elem is not None:
                for alias in aliases_elem.findall('Alias'):
                    if alias.text:
                        all_names.append(alias.text)

            # Map each name/alias to (tn_id, all_names)
            for n in all_names:
                name_to_tn[n] = (tn_id, all_names)

        # Parse CSV and check matches
        rows = []
        match_count = missing_count = 0

        with io.open(output_csv_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split(' ', 1)
                if len(parts) < 2:
                    continue
                here_id, here_name = parts[0], parts[1]

                if here_name in name_to_tn:
                    status = "Match"
                    tn_id, tn_names = name_to_tn[here_name]
                    match_count += 1
                else:
                    status = "Missing"
                    tn_id, tn_names = "", []
                    missing_count += 1

                rows.append((here_id, here_name, tn_id, tn_names, status))

        total = len(rows)
        match_rate = (match_count / total * 100) if total > 0 else 0
        is_pass = match_rate >= pass_threshold
        pass_fail = "PASS" if is_pass else "FAIL"

        if is_pass:
            os.system("aws s3 cp {} {} --recursive".format(self.data_path, self.s3_raw_data_path))

        html = '''<!DOCTYPE html>
        <html>
        <head>
        <title>TN Toll Cost Validation Report</title>
        <style>
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background: #4CAF50; color: white; }}
        .match {{ color: green; }}
        .missing {{ color: red; }}
        .pass {{ color: green; font-weight: bold; }}
        .fail {{ color: red; font-weight: bold; }}
        </style>
        </head>
        <body>
        <h1>TN Toll Cost Validation Report <span class="{0}">[{1}]</span></h1>
        <p><b>HERE Total:</b> {2} | <b>Match:</b> {3} | <b>Missing:</b> {4} | <b>Match Rate:</b> {5:.1f}% (threshold: {6}%)</p>
        <table>
        <tr><th>HERE ID</th><th>HERE Name</th><th>TN ID</th><th>TN Names</th><th>Status</th></tr>
        '''.format(pass_fail.lower(), pass_fail, total, match_count, missing_count, match_rate, pass_threshold)
        for here_id, here_name, tn_id, tn_names, status in rows:
            cls = "match" if status == "Match" else "missing"
            tn_names_str = ", ".join(tn_names) if tn_names else ""
            html += '<tr><td>{0}</td><td>{1}</td><td>{2}</td><td>{3}</td><td class="{4}">{5}</td></tr>\n'.format(
                here_id, here_name, tn_id, tn_names_str, cls, status)

        html += '</table></body></html>'

        with io.open(self.tollcost_report_file, 'w', encoding='utf-8') as f:
            f.write(html)

        main_check_result = {
            "pass": match_count,
            "warning": 0,
            "error": missing_count,
            "status": "pass" if is_pass else "error",
            "detail_link": "tn_tollcost_report.html"
        }

        return main_check_result, self.sub_check_result
