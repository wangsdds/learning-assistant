def test_home_redirects_to_ui(client):
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/ui/"


def test_ui_page_and_assets_are_available(client):
    page = client.get("/ui/")
    stylesheet = client.get("/ui/styles.css")
    script = client.get("/ui/app.js")

    assert page.status_code == 200
    assert "学习助手" in page.text
    assert stylesheet.status_code == 200
    assert script.status_code == 200
