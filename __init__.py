from .nodes import CropWithMetadata, PasteWithMetadata

NODE_CLASS_MAPPINGS = {
    "CropWithMetadata": CropWithMetadata,
    "PasteWithMetadata": PasteWithMetadata
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "CropWithMetadata": "Crop with Metadata",
    "PasteWithMetadata": "Paste with Metadata"
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]