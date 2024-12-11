import ctypes
import re

from pdfixsdk.Pdfix import (
    GetPdfix,
    PdfDoc,
    PdfImageParams,
    PdfPageRenderParams,
    PdfRect,
    PdsDictionary,
    PdsStructElement,
    kImageDIBFormatArgb,
    kImageFormatJpg,
    kPdsStructChildElement,
    kRotate0,
    kSaveFull,
)

from ai import table_summary


def render_page(doc: PdfDoc, page_num: int, bbox: PdfRect, zoom: float) -> bytearray:
    page = doc.AcquirePage(page_num)
    page_view = page.AcquirePageView(zoom, kRotate0)

    rect = page_view.RectToDevice(bbox)

    # render content
    render_params = PdfPageRenderParams()
    render_params.matrix = page_view.GetDeviceMatrix()
    render_params.clip_box = bbox
    render_params.image = GetPdfix().CreateImage(
        rect.right - rect.left,
        rect.bottom - rect.top,
        kImageDIBFormatArgb,
    )
    page.DrawContent(render_params)

    # save image to stream and data
    stm = GetPdfix().CreateMemStream()
    img_params = PdfImageParams()
    img_params.format = kImageFormatJpg
    render_params.image.SaveToStream(stm, img_params)

    data = bytearray(stm.GetSize())
    raw_data = (ctypes.c_ubyte * len(data)).from_buffer(data)
    stm.Read(0, raw_data, len(data))

    # cleanup
    stm.Destroy()
    render_params.image.Destroy()
    page_view.Release()
    page.Release()

    return data


def get_page_number_from_elem(elem: PdsStructElement, doc: PdfDoc) -> int:
    page_num = elem.GetPageNumber(0)
    if page_num != -1:
        return page_num

    for i in range(elem.GetNumChildren()):
        child_dict = elem.GetChildObject(i)
        child_elem = doc.GetStructTree().GetStructElementFromObject(child_dict)

        for j in range(child_elem.GetNumChildren()):
            page_num = child_elem.GetChildPageNumber(j)
            if page_num != -1:
                return page_num
    return -1


def update_table_sum(
    elem: PdsStructElement,
    doc: PdfDoc,
    api_key: str,
    overwrite: bool,
    lang: str,
) -> None:
    img = "image_" + str(elem.GetObject().GetId()) + ".jpg"
    # get image bbox from attributes
    bbox = PdfRect()
    for i in range(0, elem.GetNumAttrObjects()):
        attr = PdsDictionary(elem.GetAttrObject(i).obj)
        arr = attr.GetArray("BBox")
        if not arr:
            continue
        bbox.left = arr.GetNumber(0)
        bbox.bottom = arr.GetNumber(1)
        bbox.right = arr.GetNumber(2)
        bbox.top = arr.GetNumber(3)
        break

    # check bounding box
    if bbox.left == bbox.right or bbox.top == bbox.bottom:
        print("[" + img + "] table found but no BBox attribute was set")
        return

    # get the object page number (it may be written in child objects)
    page_num = get_page_number_from_elem(elem, doc)
    if page_num == -1:
        print("[" + img + "] table found but can't determine the page number")
        return

    data = render_page(doc, page_num, bbox, 1)
    with open(img, "wb") as bf:
        bf.write(data)

    response = table_summary(img, api_key, lang)

    # print(response.message.content)
    alt = response.message.content

    org_alt = elem.GetAlt()

    if overwrite or not org_alt:
        elem.SetAlt(alt)


def browse_table_tags(
    parent: PdsStructElement,
    doc: PdfDoc,
    tags: str,
    api_key: str,
    overwrite: bool,
    lang: str,
) -> None:
    count = parent.GetNumChildren()
    struct_tree = doc.GetStructTree()
    for i in range(0, count):
        if parent.GetChildType(i) != kPdsStructChildElement:
            continue
        child_elem = struct_tree.GetStructElementFromObject(parent.GetChildObject(i))
        if re.match(tags, child_elem.GetType(True)):
            # process figure element
            update_table_sum(child_elem, doc, api_key, overwrite, lang)
        else:
            browse_table_tags(child_elem, doc, tags, api_key, overwrite, lang)


def alt_text(
    input_path: str,
    output_path: str,
    tags: str,
    license_name: str,
    license_key: str,
    api_key: str,
    overwrite: bool,
    lang: str,
) -> None:
    """Run OpenAI for alternate text description.

    Parameters
    ----------
    input_path : str
        Input path to the PDF file.
    output_path : str
        Output path for saving the PDF file.
    license_name : str
        Pdfix SDK license name.
    license_key : str
        Pdfix SDK license key.
    api_key : str
        OpenAI API key.
    overwrite : bool
        Ovewrite alternate text if already present.
    lang : str
        Alternate description language.

    """
    pdfix = GetPdfix()
    if pdfix is None:
        raise Exception("Pdfix Initialization fail")

    if license_name and license_key:
        if not pdfix.GetAccountAuthorization().Authorize(license_name, license_key):
            raise Exception("Pdfix Authorization fail")
    else:
        print("No license name or key provided. Using Pdfix trial")

    # Open doc
    doc = pdfix.OpenDoc(input_path, "")
    if doc is None:
        raise Exception("Unable to open pdf : " + str(pdfix.GetError()))

    struct_tree = doc.GetStructTree()
    if struct_tree is None:
        raise Exception("PDF has no structure tree : " + str(pdfix.GetError()))

    child_elem = struct_tree.GetStructElementFromObject(struct_tree.GetChildObject(0))
    try:
        browse_table_tags(child_elem, doc, tags, api_key, overwrite, lang)
    except Exception as e:
        raise e

    if not doc.Save(output_path, kSaveFull):
        raise Exception("Unable to save PDF " + str(pdfix.GetError()))
