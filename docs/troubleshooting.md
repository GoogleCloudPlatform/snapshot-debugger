# Snapshot Debugger Troubleshooting

If you run into problems with Snapshot Debugger, file an
[issue](https://github.com/GoogleCloudPlatform/snapshot-debugger/issues).

## Your project doesn’t show up when enabling Firebase

### Symptom

Your project id is not auto populated and is not present in the project dropdown
when you try to [Enable Firebase for your GCP Project][enable-firebase]

### Resolution

Check if the Firebase Management API is already enabled, as if it is, that
interferes with the process. Try using the following link to disable the
Firebase Management API, then go back and follow the steps in the [Enable
Firebase for your GCP Project][enable-firebase]

```
https://console.developers.google.com/apis/api/firebase.googleapis.com?project=PROJECT_ID
```

Where PROJECT_ID is your project ID.

## Your database in not displayed in the Firebase Console

### Symptom

A blank screen is shown when attempting to view database contents in Firebase
Console's Realtime Database section. The project is using the Blaze pricing
plan.

### Resolution

Rerun the init command to find the database's url. Use that url to view the
database's contents. See [Blaze plan RTDB setup][blaze-plan-setup] for
details, as noted there, it is safe to run the `init` command multiple times to
view your database's information.

The database's url should resemble `https://DATABASE_NAME.firebaseio.com`,
which should redirect to
`https://console.firebase.google.com/project/PROJECT_ID/database/DATABASE_NAME/data`
for the Firebase Console view.

[enable-firebase]: https://github.com/GoogleCloudPlatform/snapshot-debugger/blob/main/README.md#enable-firebase-for-your-google-cloud-project
[blaze-plan-setup]: https://github.com/GoogleCloudPlatform/snapshot-debugger/blob/main/README.md#blaze-plan-rtdb-setup
