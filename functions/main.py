# Welcome to Cloud Functions for Firebase for Python!
# To get started, simply uncomment the below code or create your own.
# Deploy with `firebase deploy`

from firebase_functions import https_fn, options
from firebase_admin import initialize_app, auth, firestore, credentials

options.set_global_options(max_instances=50)


cred = credentials.Certificate("service_account.json")
initialize_app(credential=cred)
db = firestore.client()


# get all Users

@https_fn.on_call()
def get_all_users(req: https_fn.CallableRequest) -> any:
    try:
        users = auth.list_users()
        users_list = []
        for user in users.iterate_all():
            user_dict = {
                'uid': user.uid,
                'email': user.email,
                'display_name': user.display_name,
                # Add more user attributes as needed
            }

            # Get the masjid_allocated field from Firestore
            user_doc = db.collection('Users').document(user.uid).get()
            if user_doc.exists:
                try:
                    print(f"user doc value: ${user_doc.get('masjid_allocated')}")
                    user_dict['masjid_allocated'] = [masjid.path.split("/")[1] for masjid in user_doc.get('masjid_allocated') ]
                    
                except Exception as e:
                    pass
                

            users_list.append(user_dict)
            return {"users": users_list}
    except Exception as e:
        raise https_fn.HttpsError(code=https_fn.FunctionsErrorCode.NOT_FOUND, message=f"An error Occurred{e}")

# add User

@https_fn.on_call()
def add_user(req: https_fn.CallableRequest) -> any:
    try:
        data = req.data
        email = data['email']
        display_name = data['displayName']
        password = data.get('password')  # Use .get() to get the password if it exists
        masjid_doc_names = data['masjidDocNames']
        

        try:
            if auth.get_user_by_email(email=email):
                raise https_fn.HttpsError(code=https_fn.FunctionsErrorCode.ALREADY_EXISTS, message=f"User with email {email} Already Exists.")
        except Exception as e:
            pass

        if password:
            user = auth.create_user(
                email=email,
                display_name=display_name,
                password=password
            )
        else:
            user = auth.create_user(
                email=email,
                display_name=display_name,
            )

        # Add user document to Firestore
        user_ref = db.collection('Users').document(user.uid)
        user_ref.set({
            'isAdmin': False,
            'isStaff': True,
            'masjid_allocated': [db.collection('Masjid').document(doc_name) for doc_name in masjid_doc_names]
        })

        return {'message': 'User created successfully'}

    except Exception as e:
        raise https_fn.HttpsError(code=https_fn.FunctionsErrorCode.ABORTED, message=f"An Error Occurred. Error: {e}")
    

# get password reset link

@https_fn.on_call()
def get_password_reset_link(req: https_fn.CallableRequest) -> any:
    try:
        email = req.data["email"]
        link = auth.generate_password_reset_link(email=email)
        return {"link": link }
    except Exception as e:
        raise https_fn.HttpsError(code=https_fn.FunctionsErrorCode.ABORTED, message="Failed to get password reset link.")


# delete user

@https_fn.on_call()
def delete_user(req: https_fn.CallableRequest) -> any:
    try:
        uid = req.data["uid"]

        # Delete the user from Firebase Authentication
        try:
            auth.delete_user(uid=uid)
        except Exception as e:
            raise https_fn.HttpsError(code=https_fn.FunctionsErrorCode.ABORTED, message="Failed to delete user")


        # Delete the Firestore collection with the same UID as the user
        try:
            user_doc_ref = db.collection('Users').document(uid)
            user_doc_ref.delete()
        except Exception as e:
            raise https_fn.HttpsError(code=https_fn.FunctionsErrorCode.ABORTED, message="Failed to delete Collection")

        return {"message": "Account and associated Firestore data deleted successfully"}

    except Exception as e:
        raise https_fn.HttpsError(code=https_fn.FunctionsErrorCode.ABORTED, message="Failed to delete user")
        
