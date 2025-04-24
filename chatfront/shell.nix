{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    bun
    nodejs_20  # For types and compatibility
    nodePackages.typescript
    nodePackages.typescript-language-server
  ];

  shellHook = ''
    echo "Bun development environment loaded"
    export PATH=$PWD/node_modules/.bin:$PATH
  '';
} 