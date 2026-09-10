"""Keep retired resource URLs usable after their text moves into a collection."""
from html import escape
import hashlib
import json
from pathlib import Path, PurePosixPath
import posixpath
import re

from mkdocs.structure.files import File
from mkdocs.utils.meta import get_data

_aliases = []


def on_pre_build(config):
    _aliases.clear()


def on_files(files, config):
    # Retain explicitly frozen originals on disk while publishing compatibility
    # entries. A changed original must be reconciled, never silently shadowed.
    retained = []
    for file in files.documentation_pages():
        text = Path(file.abs_src_path).read_text(encoding='utf-8')
        if 'resource_aliases:' not in text:
            continue
        _, meta = get_data(text)
        for alias in meta.get('resource_aliases', []):
            expected = alias.get('preserved_source_sha256')
            if not expected:
                continue
            source = str(PurePosixPath(file.src_uri).parent / alias['path'])
            original = files.get_file_from_path(source)
            if not original or hashlib.sha256(Path(original.abs_src_path).read_text(encoding='utf-8').encode('utf-8')).hexdigest() != expected:
                raise ValueError(f'Preserved source changed; reconcile with collection: {source}')
            retained.append(original)
    for original in retained:
        files.remove(original)
    return files


def on_post_page(output, page, config):
    discussion_links = []
    for alias in page.meta.get('resource_aliases', []):
        name = alias['path']
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]*\.md', name):
            raise ValueError(f'Invalid resource alias: {name}')
        source = str(PurePosixPath(page.file.src_uri).parent / name)
        if (Path(config.docs_dir) / source).exists() and not alias.get('preserved_source_sha256'):
            raise ValueError(f'Resource alias would replace a source page: {source}')
        old = File(source, config.docs_dir, config.site_dir, config.use_directory_urls)
        relative = posixpath.relpath(page.file.url, posixpath.dirname(old.url))
        if page.file.url.endswith('/'):
            relative += '/'
        targets = [alias['target'], *alias.get('anchors', {}).values()]
        if any(f'id="{escape(target, quote=True)}"' not in output for target in targets):
            raise ValueError(f'Resource alias has a missing target: {source}')
        comment_script = re.search(r'<script\s+src="https://giscus.app/client.js"[\s\S]*?</script>', output)
        comment_attributes = dict(re.findall(r'([\w-]+)="([^"]*)"', comment_script[0])) if comment_script else {}
        _aliases.append((old.dest_path, relative, alias, comment_attributes))
        if comment_attributes:
            title_match = re.search(r'<section[^>]*id="' + re.escape(alias['target']) + r'"[^>]*data-export-title="([^"]+)"', output)
            label = alias.get('label') or (title_match[1] if title_match else name.removesuffix('.md'))
            discussion_url = posixpath.relpath(old.url, posixpath.dirname(page.file.url)) + ('/' if old.url.endswith('/') else '') + '?comments=1'
            discussion_links.append('<li><a data-instant="false" href="' + escape(discussion_url, quote=True) + '">' + escape(label) + '</a></li>')
    if discussion_links:
        links = '<details class="resource-legacy-comments"><summary>原页讨论</summary><ul>' + ''.join(discussion_links) + '</ul></details>'
        output = output.replace('<h2 id="__comments">', links + '<h2 id="__comments">', 1)
    return output


def on_post_build(config):
    seen = set()
    for destination, relative, alias, comments in _aliases:
        if destination in seen:
            raise ValueError(f'Duplicate resource alias: {destination}')
        seen.add(destination)
        target = relative + '#' + alias['target']
        export = relative + '#' + alias['export']
        anchors = json.dumps(alias.get('anchors', {}), ensure_ascii=True).replace('<', '\\u003c')
        script = ('const target=new URL(' + json.dumps(target) + ',location.href);'
                  'const anchors=' + anchors + ';'
                  'if(location.hash){let key;try{key=decodeURIComponent(location.hash.slice(1));}'
                  'catch{key=location.hash.slice(1);}'
                  'target.hash=Object.hasOwn(anchors,key)?anchors[key]:key;}'
                  'target.search=location.search;'
                  'if(!new URLSearchParams(location.search).has("comments")&&location.hash!=="#__comments")location.replace(target.href);')
        html = ('<!doctype html><html lang="zh"><head><meta charset="utf-8">'
                '<meta name="robots" content="noindex">'
                '<meta name="resource-export-source" content="' + escape(export, quote=True) + '">'
                '<link rel="canonical" href="' + escape(relative, quote=True) + '">'
                '<script>' + script + '</script>'
                '<title>原页讨论</title></head><body><main style="max-width:48rem;margin:2rem auto;padding:0 1rem">'
                '<p><a href="' + escape(target, quote=True) + '">打开合集中的对应资料</a></p>'
                '<div id="legacy-discussion"></div></main><script>'
                'if(new URLSearchParams(location.search).has("comments")||location.hash==="#__comments"){'
                'const script=document.createElement("script");const attrs=' + json.dumps(comments).replace('<', '\\u003c') + ';'
                'for(const [key,value] of Object.entries(attrs))script.setAttribute(key,value);'
                'script.async=true;document.querySelector("#legacy-discussion").append(script);}'
                '</script></body></html>')
        path = Path(config.site_dir) / destination
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding='utf-8')
