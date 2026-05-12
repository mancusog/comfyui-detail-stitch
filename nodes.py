import torch.nn.functional as F
import torch

class CropWithMetadata:
    CATEGORY = "Detail Stitch"
    RETURN_TYPES = ("IMAGE", "CROP_INFO", "STRING")
    FUNCTION = "crop_with_metadata"
    RETURN_NAMES = ("Cropped Image", "Crop Metadata", "warnings")
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "x": ("INT", {"default": 0, "min": 0, "max": 8192}),
                "y": ("INT", {"default": 0, "min": 0, "max": 8192}),
                "width": ("INT", {"default": 512, "min": 1, "max": 8192, "step": 8}),
                "height": ("INT", {"default": 512, "min": 1, "max": 8192, "step": 8}),
                "padding_mode": (["pixels", "percent"],),
                "padding": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1024.0, "step": 1.0}),
            },
            "optional": {
                "mask": ("MASK",)
            }
        }
    
    def crop_with_metadata (self, image, x, y, width, height, padding_mode, padding, mask=None):
        _, img_h, img_w, _  = image.shape
        warnings = []

        if mask is not None:
            nonzero = mask[0].nonzero()
            if nonzero.numel() == 0:
                warnings.append("Mask is empty. No cropping applied.")
            else:
                y_min = int(nonzero[:, 0].min().item())
                y_max = int(nonzero[:, 0].max().item())
                x_min = int(nonzero[:, 1].min().item())
                x_max = int(nonzero[:, 1].max().item())

                bbox_w = x_max - x_min + 1
                bbox_h = y_max - y_min + 1

                if padding_mode == "pixels":
                    pad_x = int(padding)
                    pad_y = int(padding)
                else: #padding_mode == "percent"
                    pad_x = int(bbox_w * padding/100.0)
                    pad_y = int(bbox_h * padding/100.0)

                x = x_min - pad_x
                y = y_min - pad_y
                width = bbox_w + 2 * pad_x
                height = bbox_h + 2 * pad_y

        if x < 0:
            width += x
            x = 0
            warnings.append("bbox clamped: left edge out of bounds.")
        if y < 0:
            height += y
            y = 0
            warnings.append("bbox clamped: top edge out of bounds.")
        if x + width > img_w:
            width = img_w - x
            warnings.append("bbox clamped: right edge out of bounds.")
        if y + height > img_h:
            height = img_h - y
            warnings.append("bbox clamped: bottom edge out of bounds.")

        cropped_image = image[:, y:y+height, x:x+width, :]
        crop_info = {
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "original_width": img_w,
            "original_height": img_h
        }
            
        warnings_string = "\n".join(warnings)
        return (cropped_image, crop_info, warnings_string)

class PasteWithMetadata:
    CATEGORY = "Detail Stitch"
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "paste_with_metadata"
    RETURN_NAMES = ("Composited Image",)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "original_image": ("IMAGE",),
                "crop_image": ("IMAGE",),
                "crop_info": ("CROP_INFO",),
            },
            "optional": {
                "mask": ("MASK",),
                "exclude_mask": ("MASK",)
            }
        }
    
    def paste_with_metadata(self, original_image, crop_image, crop_info, mask=None, exclude_mask=None):
        x = crop_info["x"]
        y = crop_info["y"]
        width = crop_info["width"]
        height = crop_info["height"]
        original_width = crop_info["original_width"]
        original_height = crop_info["original_height"]

        original_image = original_image.clone()
        _, crop_h, crop_w, _ = crop_image.shape
        if crop_h != height or crop_w != width:
            crop_image_permuted = crop_image.permute(0, 3, 1, 2) 
            crop_image_resized = F.interpolate(crop_image_permuted, size=(height, width), mode='bilinear', align_corners=False)
            crop_image = crop_image_resized.permute(0, 2, 3, 1)

        if mask is not None:
            if mask.shape[1] == original_image.shape[1] and mask.shape[2] == original_image.shape[2]:
                mask = mask[:, y:y+height, x:x+width]
            if mask.shape[1] != height or mask.shape[2] != width:
                mask = mask.unsqueeze(1)
                mask = F.interpolate(mask, size=(height, width), mode='nearest')
                mask = mask.squeeze(1)
            mask_unsqueezed = mask.unsqueeze(-1)

            if exclude_mask is not None:
                if exclude_mask.shape[1] == original_image.shape[1] and exclude_mask.shape[2] == original_image.shape[2]:
                    exclude_mask = exclude_mask[:, y:y+height, x:x+width]
                if exclude_mask.shape[1] != height or exclude_mask.shape[2] != width:
                    exclude_mask = exclude_mask.unsqueeze(1)
                    exclude_mask = F.interpolate(exclude_mask, size=(height, width), mode='bilinear', align_corners=False)
                    exclude_mask = exclude_mask.squeeze(1)
                exclude_mask_unsqueezed = exclude_mask.unsqueeze(-1)
                mask_unsqueezed = mask_unsqueezed * (1 - exclude_mask_unsqueezed)
            composited_image = mask_unsqueezed * crop_image + (1 - mask_unsqueezed) * original_image[:, y:y+height, x:x+width, :]
            original_image[:, y:y+height, x:x+width, :] = composited_image
        else:
            original_image[:, y:y+height, x:x+width, :] = crop_image

        return (original_image,)