from invoicing.domain.field_names import human_field


def test_field_names_are_readable() -> None:
    assert human_field("lines[0].quantity") == "Quantité, ligne 1"
    assert human_field("customer.name") == "Client"
    assert human_field("inconnu") == "inconnu"
