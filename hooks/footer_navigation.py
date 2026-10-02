"""Choose useful page-end destinations instead of traversing the whole site."""
from pathlib import PurePosixPath


def on_page_context(context, page, config, nav):
    footer = {}
    context["bms_footer"] = footer
    source = PurePosixPath(page.file.src_uri)
    if source.name == "index.md" or "footer" in (page.meta.get("hide") or []):
        return context

    if source.parts[0] == "courses" and len(source.parts) >= 3:
        # Resolve an existing, navigable index from nearest group to course.
        # A nested section without its own index returns to the enclosing one.
        pages = {item.file.src_uri: item for item in nav.pages}
        course = PurePosixPath(*source.parts[:2])
        for directory in source.parents:
            target = pages.get(str(directory / "index.md"))
            if target:
                footer["return_to"] = {
                    "url": target.url,
                    "title": target.meta.get("title") or target.title,
                }
                break
            if directory == course:
                break
    elif source.parts[0] == "feiyue":
        # The handbook has a reading sequence, bounded by its own section.
        for direction in ("previous", "next"):
            target = getattr(page, direction + "_page")
            if target and target.file.src_uri.startswith("feiyue/"):
                footer[direction] = target
    return context
