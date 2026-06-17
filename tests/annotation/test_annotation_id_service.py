from contract_diff.annotation.services.annotation_id_service import AnnotationIdService


def test_annotation_id_service_generates_unique_sequential_ids() -> None:
    service = AnnotationIdService()

    ids = tuple(service.next_id() for _ in range(3))

    assert ids == ("ANN-1", "ANN-2", "ANN-3")
    assert len(set(ids)) == 3


def test_annotation_id_service_accepts_custom_prefix() -> None:
    service = AnnotationIdService(prefix="NOTE")

    assert service.next_id() == "NOTE-1"
