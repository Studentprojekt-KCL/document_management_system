# Vue 3 + Vite

This template should help get you started developing with Vue 3 in Vite. The template uses Vue 3 `<script setup>` SFCs, check out the [script setup docs](https://v3.vuejs.org/api/sfc-script-setup.html#sfc-script-setup) to learn more.

Learn more about IDE Support for Vue in the [Vue Docs Scaling up Guide](https://vuejs.org/guide/scaling-up/tooling.html#ide-support).

# Building and Running Code

# Build Instructions
docker build -t test_frontend .

## Run instructions after build
docker run --rm -d --name test_frontend_run -p 8080:80 test_frontend

## Open a browers and enter localhost
http://localhost:8080

## To stop docker
docker stop test_frontend_run

# To run and see live changes
## install npm
npm install

## run npm
npm run dev

## To stop
ctrl + c

# Troubleshooting, If you get errors:
## Note: Vite might require node of 20.19+ 
## check node.js version
node -v

## One way to fix it: (Ubuntu)
## remove the old node
sudo apt remove node.js

## donwload new node
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo bash -
sudo apt-get install -y nodejs

## After this the npm run dev should work. It will run the on adress: http://localhost:5173


# Accessing the DMS

The only way to access the DMS now is through logging in.
Any attempt to bypass the path by adding /search would result in being redirected to the / path.
1. http://localhost:8080 / http://localhost:5173
2. press login
3. enter credentials
- frontend_tester
- password
4. gain access to DMS

# Keycloak
To access keycloak you can go to: https://ad.dms-lookup.com:8443/
## creating a user
Use the admin credentials to log in
Choose User from the left side bar
1. Add User
- Leave required user actions empty
- Leave email verified off
+ Username
+ email
+ first name
+ last name
2. Create
3. Credentials
4. set password
+ enter password
+ re-enter password
- leave temporary off
5. save password

## Test account
username: frontend_tester
password: password