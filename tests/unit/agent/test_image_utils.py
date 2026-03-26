import base64

from meto.agent.image_utils import detect_images_in_prompt, encode_image, is_image


def test_is_image(tmp_path):
    img_path = tmp_path / "test.png"
    img_path.write_bytes(b"dummy")
    txt_path = tmp_path / "test.txt"
    txt_path.write_text("not an image")

    assert is_image(str(img_path)) is True
    assert is_image(str(txt_path)) is False
    assert is_image("nonexistent.png") is True  # mimetypes doesn't care about existence


def test_encode_image(tmp_path):
    img_path = tmp_path / "test.png"
    data = b"fake-image-data"
    img_path.write_bytes(data)

    mime, encoded = encode_image(str(img_path))

    assert mime == "image/png"
    assert encoded == base64.b64encode(data).decode("utf-8")


def test_detect_images_in_prompt(tmp_path):
    # Create a real image file
    img_path = tmp_path / "screenshot.png"
    img_path.write_bytes(b"dummy")

    # Create a non-image file with image extension (should still be detected if mimetypes says so,
    # but the implementation in the plan also checks is_image which uses mimetypes)
    other_img = tmp_path / "photo.jpg"
    other_img.write_bytes(b"dummy")

    # Non-existent file
    non_existent = tmp_path / "ghost.png"

    # Text file
    txt_file = tmp_path / "notes.txt"
    txt_file.write_text("some notes")

    prompt = f"Check {img_path}, {other_img}, {non_existent}, and {txt_file}"
    found = detect_images_in_prompt(prompt)

    assert len(found) == 2
    assert str(img_path) in found
    assert str(other_img) in found
    assert str(non_existent) not in found
    assert str(txt_file) not in found
