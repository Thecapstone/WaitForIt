from rest_framework.decorators import throttle_classes
from rest_framework.response import Response
import rest_framework.status as status
from rest_framework.throttling import UserRateThrottle
from rest_framework.viewsets import ModelViewSet

from authentication.models import User as user_db
from memories.models import Capsule as capsule_db
from memories.serializers import (
    CapsuleCreationSerializer,
    CapsuleJoinSerializer,
    CapsulePreviewSerializer,
    CapsuleUpdateSerializer,
    CapsuleViewSerializer,
)


class TwicePerDayUserThrottle(UserRateThrottle):
    rate = "2/day"


class CapsuleViewSet(ModelViewSet):
    queryset = capsule_db.objects.all()
    serializer_class = CapsuleCreationSerializer

    @throttle_classes(TwicePerDayUserThrottle)
    def create(self, request):
        serializer = CapsuleCreationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(creator=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def preview(self, request, pk):
        """
        retrieve specific information about the capsule(such as; description, teaser, title, avatar??), before it is unlocked
        access to this feature depends on the privacy of the capsule.
        """
        try:
            capsule = capsule_db.objects.get(id=pk)
        except capsule_db.DoesNotExist:
            return Response(
                {"Capsule": "Capsule does not exist"}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = CapsulePreviewSerializer(capsule)

        if request.user == capsule.creator or request.user == capsule.members:
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(
            {"message": "Cannot access this capsule"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    def retrieve(self, request, pk):
        """
        retrieve all data stored in a capsule, by members, once the open date reaches.
        """
        try:
            capsule = capsule_db.objects.get(id=pk)
        except capsule_db.DoesNotExist:
            return Response(
                {"Capsule": "Capsule does not exist"}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = CapsuleViewSerializer(capsule)

        if request.user != capsule.member and not capsule.is_open:
            return Response(
                {"message": "Cannot access this capsule"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return Response(
            {
                "data": serializer.data,
                "message": "Here's a glimpse of your stored memories.",
            },
            status=status.HTTP_200_OK,
        )

    def update(self, request, pk):
        """
        restricts the ability to update capsule data to contributors and creators,
        other non-priviledged members are prevented
        """
        try:
            capsule = capsule_db.objects.get(id=pk)
        except capsule_db.DoesNotExist:
            return Response(
                {"Capsule": "Capsule does not exist"}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = CapsuleUpdateSerializer(capsule)

        if request.user == capsule.creator or request.user == capsule.contributors:
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(
            {"message": "Cannot access this capsule"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    def join_capsule(self, request, pk):
        """
        returns the id of the user and the id of the capsule they want to join.
        """
        try:
            capsule = capsule_db.objects.get(id=pk)
        except capsule_db.DoesNotExist:
            return Response(
                {"Capsule": "Capsule does not exist"}, status=status.HTTP_404_NOT_FOUND
            )

        data = {"user_id": request.user, "capsule_id": capsule}
        serializer = CapsuleJoinSerializer(data=data)

        if serializer.is_valid:
            serializer.save()
            capsule.members.add(request.user)
            user_db.objects.get(id=request.user.id).capsules_joined.add(capsule)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(
            {"message": "Capsule or user not found"}, status=status.HTTP_400_BAD_REQUEST
        )

    # likely need to seperate the adding of new members and the adding of new contributors.
    def add_new_member_to_capsule(self, request, capsule_id, user_id):
        """
        #retrieves capsule with a given id and the id of the user to be made a contributor,
        #adds the capsule id to the 'capsules_contributed_to reverse many-to-many user field,
        #finally add the user id to the contributors list which grants them specific permissions.
        """
        try:
            capsule = capsule_db.objects.get(id=capsule_id)
        except capsule_db.DoesNotExist:
            return Response(
                {"Capsule": "Capsule does not exist"}, status=status.HTTP_404_NOT_FOUND
            )
        try:
            user = user_db.objects.get(id=user_id)
        except user_db.DoesNotExist:
            return Response(
                {"message": "User not found"}, status=status.HTTP_400_BAD_REQUEST
            )

        if request.user == capsule.creator and request.user not in capsule.contributors:
            capsule.contributors.add(user)
            user.capsules_contributed_to.add(capsule)
            return capsule
        return Response(
            {"message": "Unauthorized to share this capsule"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # Creator:
    # can create a capsule
    # can update capsule
    # can add contributors and members
    # can remove contributors and members
    # can preview capsule

    # Contributor:
    # can update capsule
    # can preview capsule

    # Member:
    # can view capsule

    # Capsule:
    # opening date
    # .....

    # get all public
    # everyone

    # get all by joined ID:
    # creator and contributors

    # 1 get users profile by the current signed in users id
    # 2 get capsules_contributed_to field,
    # 3 add the capsule to it, if it doesnt exist
    # 4 update profile with updated contributed_to field

    # concern: if contributors are also on members list, querying lists_joined will produce same capsule twice to account for
    # a capsule which a user is a member of and a contributor of,
    # but i need that for viewing restrictions,
    # instead of specifying capsule creator, member, and contributor, will be neater to say
    # if capsule.member and it includes all...?
