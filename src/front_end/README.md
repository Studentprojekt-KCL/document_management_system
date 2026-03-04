# Vue 3 + Vite

This template should help get you started developing with Vue 3 in Vite. The template uses Vue 3 `<script setup>` SFCs, check out the [script setup docs](https://v3.vuejs.org/api/sfc-script-setup.html#sfc-script-setup) to learn more.

Learn more about IDE Support for Vue in the [Vue Docs Scaling up Guide](https://vuejs.org/guide/scaling-up/tooling.html#ide-support).
________________________________________

# Building and Running Code

## Using Docker

### Build Instructions
```docker build -t test_frontend .```

### Run instructions after build
```docker run --rm -d --name test_frontend_run -p 8080:80 test_frontend```

**Open a brower and enter:** ```http://localhost:8080```

### Stop docker
```docker stop test_frontend_run```

## To run npm and see live changes
### Install npm
```npm install```

### Run npm
```npm run dev```

### To stop
ctrl + c
________________________________________

## Troubleshooting, If you get errors:
### Note: Vite might require node of 20.19+ 
**check node.js version**

```node -v```

### One way to fix it: (Ubuntu)
- **Remove the old node**

sudo apt remove node.js

- **Donwload new node**

```curl -fsSL https://deb.nodesource.com/setup_22.x | sudo bash -```

```sudo apt-get install -y nodejs```

**After this the npm run dev should work. It will run the on adress:** ```http://localhost:5173```
________________________________________

# Accessing the DMS

The only way to access the DMS now is through logging in.
Any attempt to bypass the path by adding /search would result in being redirected to the / path.
1. ```http://localhost:8080``` / ```http://localhost:5173```
2. Rress login
3. Enter credentials
   > frontend_tester

   > password
5. Access to DMS
________________________________________

# Keycloak
To access keycloak you can go to: ```https://ad.dms-lookup.com:8443/```
## Create a user
Use the admin credentials to log in (*admin, pass*).

Choose User from the left side bar.

1. **Add User**
   - Leave required user actions empty
   - Leave email verified off
        - Username
        - Email
        - First name
        - Last name
2. **Create**
3. **Credentials**
4. **Set password**
    - Enter password
    - Re-enter password
    - Leave temporary off
5. **Save password**
________________________________________

### Test account
**username:** frontend_tester
**password:** password

________________________________________

# Environment Setup
Before running the service, you must create a `.env` file in the /front_end/ directory.

Create `.env` file following this structure:

```
VITE_KEYCLOAK_BASE =https://ad.dms-lookup.com:8443
VITE_REALM =master
VITE_CLIENT_ID =dms-frontend
```

## testing roles
### Web Browser Testing
f12 -> console:

`hasRole("admin")`
`hasRole("user")`
