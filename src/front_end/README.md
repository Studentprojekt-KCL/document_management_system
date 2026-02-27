# Vue 3 + Vite

This template should help get you started developing with Vue 3 in Vite. The template uses Vue 3 `<script setup>` SFCs, check out the [script setup docs](https://v3.vuejs.org/api/sfc-script-setup.html#sfc-script-setup) to learn more.

Learn more about IDE Support for Vue in the [Vue Docs Scaling up Guide](https://vuejs.org/guide/scaling-up/tooling.html#ide-support).

# Build Instructions
docker build -t test_frontend .

# Run instructions after build
docker run --rm -d --name test_frontend_run -p 8080:80 test_frontend

# Open a browers and enter localhost
http://localhost:8080

# To stop docker
docker stop test_frontend_run

# see live changes

# install npm
npm install

# run npm
npm run dev

# To stop
ctrl + c

# IF you get errors:

# Note: Vite might require node of 20.19+ 
# check node.js version
node -v
# One way to fix it: (Ubuntu)
# remove the old node
sudo apt remove node.js
# donwload new node
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo bash -
sudo apt-get install -y nodejs
# After this the npm run dev should work. It will run the on adress: http://localhost:5173


