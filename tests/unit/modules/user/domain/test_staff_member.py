import uuid

from src.modules.user.domain.entities import StaffMember


class TestStaffMemberCreate:
    def test_create_from_invitation(self):
        identity_id = uuid.uuid4()
        invited_by = uuid.uuid4()
        staff = StaffMember.create_from_invitation(
            identity_id=identity_id,
            profile_email="staff@company.com",
            invited_by=invited_by,
            first_name="Jane",
            last_name="Doe",
        )
        assert staff.id == identity_id
        assert staff.first_name == "Jane"
        assert staff.invited_by == invited_by
        assert staff.position is None
        assert staff.department is None


class TestStaffMemberUpdate:
    def test_update_position_and_department(self):
        staff = StaffMember.create_from_invitation(
            identity_id=uuid.uuid4(),
            profile_email="s@c.com",
            invited_by=uuid.uuid4(),
        )
        staff.update_profile(position="CTO", department="Engineering")
        assert staff.position == "CTO"
        assert staff.department == "Engineering"
