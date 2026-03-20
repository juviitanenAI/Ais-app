import sys

with open('app/templates/map_ui.html', 'r', encoding='utf-8') as f:
    content = f.read()

# EXTRACT CSS
start_style = content.find('<style>')
end_style = content.find('</style>') + len('</style>')
css_content = content[start_style + len('<style>'):content.find('</style>')].strip()

with open('app/static/css/map_ui.css', 'w', encoding='utf-8') as f:
    f.write(css_content)

new_content = content[:start_style] + '<link rel="stylesheet" href="/static/css/map_ui.css"/>' + content[end_style:]

# EXTRACT JS
start_script = new_content.rfind('<script>')
end_script = new_content.rfind('</script>') + len('</script>')
js_content = new_content[start_script + len('<script>'):new_content.rfind('</script>')].strip()

with open('app/static/js/main.js', 'w', encoding='utf-8') as f:
    f.write(js_content)

final_content = new_content[:start_script] + '<script type="module" src="/static/js/main.js"></script>' + new_content[end_script:]

with open('app/templates/map_ui.html', 'w', encoding='utf-8') as f:
    f.write(final_content)

print("Extraction complete.")
