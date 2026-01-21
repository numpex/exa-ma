import pandas as pd

# Load Excel file
df = pd.read_excel('software.xlsx')

def generate_markdown(row):
    md = f"# {row['Name']} Package\n\n"

    description = row.get('Description', '') or ''
    description = description.strip() if pd.notnull(description) else ''
    devops = row.get('DevOps', '') or ''
    license_info = row.get('License', '') or ''
    repository = row.get('Repository', '') or ''
    comments = row.get('Comments', '') or ''
    docs = row.get('Docs', '')
    docs = str(docs).strip() if pd.notnull(docs) else ''
    channels = row.get('Channels', '')
    channels = str(channels).strip() if pd.notnull(channels) else ''
    apis = row.get('API', '')
    apis = str(apis).lower() if pd.notnull(apis) else ''

    md += f"## Description\n\n"
    if description:
        md += f"{row['Description']}\n\n"
    else:
        md += "No description provided.\n\n"

    # Packaging checks based on DevOps info
    md += "## Packaging\n\n"
    md += f"* [{'x' if 'Packages' in devops else ' '}] Packages exist\n"
    md += f"* [{'x' if any(repo in devops for repo in ['Spack', 'GUIX', 'Debian', 'Ubuntu', 'Fedora']) else ' '}] Packages are published in an easily usable repository\n"
    md += f"* [{'x' if 'supercomputers' in devops.lower() else ' '}] Packages installation is tested on supercomputers\n"
    md += f"* [{'x' if any(community in devops for community in ['Spack', 'GUIX']) else ' '}] Packages are available in community repositories\n"
    if devops:
        for package in devops.split(','):
            if 'Packages' in package:
                package = package.split('Packages - ')[1].strip()
                md += f"  - {package}\n"
    md += "\n"

    # Minimal Validation Tests (heuristics based on DevOps info)
    md += "## Minimal Validation Tests\n\n"
    md += f"* [{'x' if 'Test - Unit' in devops else ' '}] unit tests exist\n"
    md += f"* [{'x' if 'Continuous Integration' in devops else ' '}] CI exists\n"
    md += f"* [{'x' if 'Continuous Delivery' in devops else ' '}] CI runs regularly (each new release)\n"
    md += f"* [{'x' if 'Continuous Integration' in devops else ' '}] CI runs regularly (each new commit in main branch)\n\n"

    # Public Repository
    md += "## Public Repository\n\n"
    md += f"* [{'x' if pd.notnull(repository) else ' '}] A repository where sources can be downloaded by anyone\n"
    md += f"* [{'x' if 'github.com' in str(repository).lower() or 'gitlab' in str(repository).lower() else ' '}] A repository where anyone can submit a modification proposition (pull request)\n"
    if repository:
        md += f"  - {repository}\n\n"
    md += "\n"

    # License Checks
    md += "## Clearly-identified license\n\n"
    md += f"* [{'x' if pd.notnull(license_info) else ' '}] Licence is clearly stated\n"
    md += f"* [{'x' if any(fl in license_info for fl in ['GPL', 'LGPL', 'MIT', 'BSD', 'Apache']) else ' '}] Licence is FLOSS licence (FSF or OSI conformant)\n"
    md += "* [ ] SPDX is used\n"
    md += "* [ ] REUSE is used\n"
    if license_info:
        for license in license_info.split(','):
            license = license.strip()
            md += f"  - {license}\n"
    md += "\n"
    # Minimal Documentation (using Comments as heuristic)
    md += "## Minimal Documentation\n\n"
    md += f"* [{'x' if docs else ' '}] Documentation exists\n"
    md += f"* [{'x' if docs.lower().startswith('https://') else ' '}] It is easily browsable online\n"
    if docs:
        for doc in docs.split(','):
            doc = doc.strip()
            md += f"  - {doc}\n\n"
    md += "\n"

    # Open Public Discussion Channel
    md += "## Open Public Discussion Channel\n\n"
    md += f"* [{'x' if channels else ' '}] A channel exist\n"
    # Assume that if any link is present, it is open and joinable freely
    md += f"* [{'x' if channels else ' '}] Anyone can join the discussion channel, free of charge, without invitation\n"

    if channels:
        # Split multiple channels separated by commas and format nicely
        for channel in channels.split(','):
            channel = channel.strip()
            md += f"  - {channel}\n"

    md += "\n"

    # Define a dictionary with metadata fields and corresponding column data
    metadata_fields = {
        "Software name": row.get('Name'),
        "Description": row.get('Description'),
        "License": row.get('License'),
        "Documentation URL": row.get('Docs'),
        "Discussion channel URL": row.get('Channels'),
        "Package repositories URLs": row.get('DevOps'),
        "Repository URL": row.get('Repository'),
        "Autoevaluation using the list of criteria stated here": 'Yes'  # Since you're generating markdown from criteria
    }

    # Check if all metadata are present (non-empty)
    all_metadata_available = all(pd.notnull(val) and str(val).strip() for val in metadata_fields.values())

    md += f"* [{'x' if all_metadata_available else ' '}] The following metadata is available:\n"

    for key, val in metadata_fields.items():
        status = '✅' if pd.notnull(val) and str(val).strip() else '❌'
        md += f"  - {key}: {status}\n"

    md += "\n"

    # codemeta check (assuming codemeta presence is explicitly mentioned in DevOps)
    codemeta_present = 'codemeta' in str(row.get('DevOps', '')).lower()
    md += f"* [{'x' if codemeta_present else ' '}] it uses codemeta format\n\n"

    # API compatibility information
    md += "## API compatibility information\n\n"
    md += f"* [{'x' if 'api changes documented' in apis else ' '}] any API addition or breakage should be documented\n"
    md += f"* [{'x' if 'semantic versioning' in apis else ' '}] Semantic Versioning is used\n"
    md += f"* [{'x' if 'release policy' in apis else ' '}] a policy easing predictability of these aspects for future release is provided\n\n"


    # Minimal Performance Tests
    md += "## Minimal Performance Tests\n\n"
    md += f"* [{'x' if 'Unit' or 'Verification' in devops else ' '}] Tests exist\n"
    md += f"* [{'x' if 'Benchmarking' in devops else ' '}] Scripts to automate launching the tests on a supercomputer and adaptable for another exist\n"
    md += "* [ ] Scripts using a tool easing portability to new HW exist\n\n"

    return md

print(df.columns.tolist())

for index, row in df.iterrows():
    benchmarked = pd.notnull(row.get('Benchmarked')) and str(row.get('Benchmarked', '')).strip().upper()
    licensed = pd.notnull(row.get('License')) and str(row.get('License', '')).strip().upper()
    packaged = pd.notnull(row.get('DevOps')) and str(row.get('DevOps', '')).strip().upper()
    if benchmarked and benchmarked != 'NOT YET' and licensed and packaged:
        print(f"Generating markdown for {row['Name']}...")         
        markdown = generate_markdown(row)
        filename = f"mds/{row['Name'].lower().replace('/', '_').replace('+', 'p').replace(' ', '_')}.md"
        with open(filename, 'w') as file:
            file.write(markdown)
        print(f"Generated {filename}")
    else:
        print(f"Skipped {row['Name']} (Benchmarked empty)")

    print(f"Generated {filename}")
print("Markdown files generated successfully!")