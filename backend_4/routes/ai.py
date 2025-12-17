from fastapi import APIRouter
from controllers import test

router = APIRouter()
router.add_api_route("/",test.say_hello, methods=["GET"])