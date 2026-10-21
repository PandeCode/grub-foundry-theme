{
  lib,
  stdenvNoCC,
  fetchurl,
  ffmpeg-headless,
  grub2,
  python3,
  dejavu_fonts,
  # image or video, a video gives its first frame
  background ? fetchurl {
    url = "https://github.com/PandeCode/nixutils/raw/refs/heads/media/sddm/factorio.mp4";
    sha256 = "0hrj4x8q068ih398gcjsr7ai6qb7mlj8mbdgcdqjcm98pjbchvaj";
  },
  # 1 for 1080p, 1.5 for 1600p, 2 for 4k
  scale ? 1,
  title ? "Boot",
  # rows shown before the list scrolls
  rows ? 10,
  # top left corner, like the game's version string
  corner ? "GRUB ${grub2.version} (${stdenvNoCC.hostPlatform.system})",
  # entries that must fit without clipping, the defaults cover nixos and
  # os-prober names
  longest ? [ ],
}:

stdenvNoCC.mkDerivation {
  pname = "grub-foundry-theme";
  version = "1.0.0";

  src = lib.fileset.toSource {
    root = ./.;
    fileset = lib.fileset.unions [
      ./build.sh
      ./gen.py
      ./fonts
    ];
  };

  nativeBuildInputs = [
    ffmpeg-headless
    grub2
    (python3.withPackages (ps: [ ps.pillow ]))
  ];

  dontBuild = true;

  installPhase = ''
    runHook preInstall

    patchShebangs build.sh
    ./build.sh \
      --scale ${toString scale} \
      --background ${background} \
      --mono ${dejavu_fonts}/share/fonts/truetype/DejaVuSansMono.ttf \
      --title ${lib.strings.escapeShellArg title} \
      --rows ${toString rows} \
      --corner ${lib.strings.escapeShellArg corner} \
      ${lib.strings.concatMapStringsSep " " (l: "--longest ${lib.strings.escapeShellArg l}") longest} \
      $out

    runHook postInstall
  '';

  meta = {
    description = "GRUB theme of factory game";
    homepage = "https://github.com/PandeCode/grub-foundry-theme";
    platforms = lib.platforms.linux;
  };
}
