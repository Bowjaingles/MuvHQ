from flask import Flask, render_template
from google_sheets_reader import get_google_sheet
import logging
import os
import importlib

logging.basicConfig(filename='core.log', level=logging.ERROR,
                    format='%(asctime)s - CORE MODULE - %(levelname)s - %(message)s')

app = Flask(__name__)

# Plugin Loader Functionality (safe and minimal)
def load_plugins(app):
    plugins_folder = 'plugins'
    for folder in os.listdir(plugins_folder):
        plugin_path = os.path.join(plugins_folder, folder)
        if os.path.isdir(plugin_path):
            plugin_main_file = f'{folder}.py'
            plugin_file_path = os.path.join(plugin_path, plugin_main_file)
            if os.path.exists(plugin_file_path):
                module_name = f'{plugins_folder}.{folder}.{folder}'
                try:
                    plugin_module = importlib.import_module(module_name)
                    if hasattr(plugin_module, 'init_plugin'):
                        plugin_module.init_plugin(app)
                        logging.info(f'Plugin loaded: {folder}')
                except Exception as e:
                    logging.error(f'Error loading plugin {folder}: {e}')

# Core routes remain explicitly unchanged
@app.route('/')
def home():
    try:
        form_responses = get_google_sheet('CMNH CUSTOMERS***', 'Form Responses 8')
        all_data = get_google_sheet('CMNH CUSTOMERS***', 'All Data')
    except Exception as e:
        form_responses = []
        all_data = []
        logging.error(f"Google Sheets fetch error: {e}")

    return render_template('index.html', form_responses=form_responses, all_data=all_data)

@app.route('/health')
def health_check():
    return {'status': 'Core Module OK'}, 200

# Explicitly load plugins
load_plugins(app)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

