# Chatbot Project

This repository contains the source code for the AI4MDE-chatbot application.

## Project Structure

The project is organized into the following main directories:

- `chatback/`: Contains the backend service code.
- `chatfront/`: Contains the frontend service code.
- `config/`: Holds configuration files for the application.
- `docs/`: Contains project documentation.
- `traefik/`: Contains configuration for Traefik, a reverse proxy and load balancer, **This service is not used yet**

## Key Files

- `chatbot-compose-dev.yml`: Docker Compose file for setting up the development environment.
- `run_interview.sh`: A script, possibly for running interviews or tests related to the chatbot.
- `.dockerignore`: Specifies files and directories to ignore when building Docker images.
- `LICENSE`: Project license file.

## Getting Started

To set up the project for local development:

1.  **Prepare the environment:**
    - Navigate to the `./config` directory.
    - For each file ending in `.example`, create a copy without the `.example` suffix (e.g., copy `chatback.env.example.yml` to `chatback.env`).
    - Edit the newly created configuration files and replace all placeholder values marked with `<change me>` with your actual configuration details.

2.  **Build the services:**
    - Open a terminal in the project root directory.
    - Run the command `podman compose -f compose.yml build` to build the Container images for the services defined in the development compose file.

3.  **Start the services:**
    - Run `podman compose -f compose.yml up -d` to start all services in detached mode.

4.  **View logs:**
    - To view the logs from all services, run `podman compose -f compose.yml logs`.
    - To follow the logs in real-time, use `podman compose -f compose.yml logs -f`.
    - To view logs from chatback service, run `podman compose -f compose.yml logs -f chatback`.
    - To view logs from chatfront service, run `podman compose -f compose.yml logs -f chatfront`.

5.  **Stop the services:**
    - Run `podman compose -f compose.yml down` to stop and remove the containers, networks, and volumes defined in the compose file.

6.  **Initial Data Setup (Manual Step):**
    - Once the services are running, you need to create an initial user and group in the database.
    - Execute the appropriate command within the `chatback` container to achieve this. The specific command is shown here:
    ```bash
    ❯ podman exec -it chatback python /chatback/scripts/add_group.py

    === Add Group Script v1.0 ===

    Group name: test-group
    Description (optional):

    Please confirm the following:
    Group Name: test-group
    Description: (none)

    Save? (Y/n) [y]: y

    Creating group 'test-group'...

    Successfully created group 'test-group' with ID: 2
    ```
    - Next you need to create a user owned by the created group.
    ```bash
    ❯ podman exec -it chatback python /chatback/scripts/add_user.py

    === Add User Script v1.0 ===

    Username: test-user
    Email: test@example.com
    Password: Secure_PassWord

    Available groups:
    - test-group

    Assign to a group? (y/N) [n]: y
    Group name: test-group

    Please confirm the following:
    Username: test-user
    Email: test@example.com
    Group: test-group

    Save? (Y/n) [y]: y

    Creating user 'test-user'...

    Successfully created user:
    Username: test-user
    Email: test@example.com
    Group: test-group
    Active: Yes
    ```
    - Other commnads are available: `del_group.py`, `del_user.py`, `groupd.py`, `mod_group.py`, `mod_user.py` and `users.py`.
    - Create the `/opt/ai4mde/data` subdirectory on your system. This directory will be used to store persistent data for the services (refer to the Compose file for details). Copy the content of `data-template` to `/opt/ai4mde/data` and rname `<test-group>` to the group-name have created. 

7.  **Access the application:**
    - Open your web browser and navigate to `http://localhost:3000`.
    - Log in using the username and password you created in the previous step (e.g., username `test-user` and the password you set).
    - The backend API is accessible at `http://localhost:8000`.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

